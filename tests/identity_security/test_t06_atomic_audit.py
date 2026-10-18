"""T06: real HTTP/reset and PostgreSQL faults, including COMMIT failures."""
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import main
from audit_outbox import encolar_evento_auditoria
from auditoria import registrar_evento

ROUTES = ["/auth/usuarios/2/mfa/restablecer", "/usuarios/2/mfa/restablecer"]


def reset_events(db):
    with db.connect() as connection:
        return connection.execute(text("""
            SELECT evento_uuid, actor_usuario_id, objetivo_usuario_id,
                   detalle, estado FROM auditoria_outbox
            WHERE evento='MFA_RESTABLECIDO_ADMIN'
        """)).mappings().all()


@pytest.mark.parametrize("route", ROUTES)
def test_reset_commits_security_and_sanitized_audit_together(client, headers, challenge, db, route):
    auth = headers(1)
    headers(2)
    challenge(2)
    response = client.post(route, headers=auth)
    assert response.status_code == 200, response.text
    rows = reset_events(db)
    assert len(rows) == 1
    event = rows[0]
    assert event["actor_usuario_id"] == 1 and event["objetivo_usuario_id"] == 2
    assert event["estado"] == "PENDIENTE"
    assert event["detalle"]["sesiones_revocadas"] == 1
    assert not any(value in json.dumps(event["detalle"]) for value in
                   ["secreto_cifrado", "otpauth", "password", "access_token", "jti"])
    with db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM mfa_totp WHERE usuario_id=2")).scalar_one() == 0


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("deferred", [False, True], ids=["insert-failure", "commit-failure"])
def test_outbox_failure_rolls_back_reset_sessions_and_challenges(db, headers, challenge, snapshot, route, deferred):
    auth = headers(1)
    headers(2)
    challenge(2)
    before = snapshot(2)
    # Fixture schema is guarded by conftest; this never targets workstation DB.
    with db.begin() as connection:
        connection.execute(text("""
            CREATE FUNCTION t06_reject_reset() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.evento='MFA_RESTABLECIDO_ADMIN' THEN
                    RAISE EXCEPTION 'fixture rejects audit';
                END IF;
                RETURN NEW;
            END $$;
        """))
        trigger = ("CREATE CONSTRAINT TRIGGER t06_reject_reset AFTER INSERT ON auditoria_outbox "
                   "DEFERRABLE INITIALLY DEFERRED" if deferred else
                   "CREATE TRIGGER t06_reject_reset BEFORE INSERT ON auditoria_outbox")
        connection.execute(text(trigger + " FOR EACH ROW EXECUTE FUNCTION t06_reject_reset()"))
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            response = client.post(route, headers=auth)
        assert response.status_code >= 500
        assert "fixture rejects audit" not in response.text and "INSERT INTO" not in response.text
        assert snapshot(2) == before
        assert reset_events(db) == []
    finally:
        with db.begin() as connection:
            connection.execute(text("DROP TRIGGER t06_reject_reset ON auditoria_outbox"))
            connection.execute(text("DROP FUNCTION t06_reject_reset()"))


@pytest.mark.parametrize("route", ROUTES)
def test_denied_reset_never_queues_success(client, headers, db, route):
    response = client.post(route, headers=headers(7))
    assert response.status_code == 403
    assert reset_events(db) == []


def event():
    return {"evento_uuid": str(uuid4()), "fecha_evento": datetime.now(timezone.utc).isoformat(),
            "servicio": "identity-service", "evento": "T06_FIXTURE", "resultado": "EXITO",
            "detalle": {"scope": "synthetic"}}


def test_transactional_enqueue_is_idempotent_without_committing_caller(db):
    record = event()
    with db.connect() as connection:
        transaction = connection.begin()
        assert encolar_evento_auditoria(record, conexion=connection)
        assert encolar_evento_auditoria(record, conexion=connection)
        assert connection.execute(text("SELECT count(*) FROM auditoria_outbox WHERE evento_uuid=CAST(:id AS UUID)"),
                                  {"id": record["evento_uuid"]}).scalar_one() == 1
        transaction.rollback()
    with db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM auditoria_outbox WHERE evento='T06_FIXTURE'")).scalar_one() == 0


@pytest.mark.parametrize("detail", [[], {"value": "x" * (17 * 1024)}])
def test_invalid_transactional_event_aborts_caller(db, detail):
    record = event()
    record["detalle"] = detail
    with pytest.raises(ValueError), db.begin() as connection:
        connection.execute(text("UPDATE mfa_totp SET activo=FALSE WHERE usuario_id=2"))
        encolar_evento_auditoria(record, conexion=connection)
    with db.connect() as connection:
        assert connection.execute(text("SELECT activo FROM mfa_totp WHERE usuario_id=2")).scalar_one() is True


def test_legacy_best_effort_contract_remains_false_for_invalid_event(db):
    assert encolar_evento_auditoria({"detalle": []}) is False


def test_transactional_audit_sanitizes_and_does_not_log_premature_success(db, monkeypatch):
    calls = []
    monkeypatch.setattr("auditoria.logger_auditoria.info", lambda value: calls.append(value))
    with db.begin() as connection:
        registrar_evento("T06_FIXTURE", conexion=connection, detalle={"password": "private-fixture"})
    assert calls == []
    with db.connect() as connection:
        detail = connection.execute(text("SELECT detalle FROM auditoria_outbox WHERE evento='T06_FIXTURE'")).scalar_one()
    assert "private-fixture" not in json.dumps(detail)


def test_legacy_stdout_cannot_forge_lines_from_user_details(db, monkeypatch):
    calls=[]
    monkeypatch.setattr("auditoria.logger_auditoria.info",lambda value:calls.append(value))
    registrar_evento("T06_SINGLE_LINE",detalle={"descripcion":"Alta\r\nFORGED\u2028\u2029á"})
    assert len(calls)==1
    value=calls[0]
    assert value.isascii() and not any(char in value for char in "\r\n\u2028\u2029")
    assert json.loads(value)["evento"]=="T06_SINGLE_LINE"
