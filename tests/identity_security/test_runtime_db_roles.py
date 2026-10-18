"""T04/T07/T14: real restricted connections, not mocked grants or admin SET ROLE."""
import secrets
import sys
from datetime import datetime, timezone
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

import main
from database import engine as admin_engine

ROLES = ["iam_identity", "iam_permissions", "iam_sync", "iam_audit", "iam_dispatcher", "iam_backup"]


@pytest.fixture
def roles(db):
    passwords = {role: secrets.token_hex(32) for role in ROLES}
    with psycopg2.connect(**dict(db.url.translate_connect_args(username="user", database="dbname"))) as connection:
        with connection.cursor() as cursor:
            for role, password in passwords.items():
                cursor.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role)), [password])
    engines = {role: create_engine(db.url.set(username=role, password=password), hide_parameters=True)
               for role, password in passwords.items()}
    try:
        yield engines
    finally:
        for engine in engines.values():
            engine.dispose()


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("statement", [
    "CREATE TABLE public.forbidden_schema_change(id integer)",
    "CREATE ROLE forbidden_admin SUPERUSER",
    "SET ROLE postgres",
    "ALTER TABLE public.usuarios_plataforma DISABLE TRIGGER ALL",
])
def test_runtime_cannot_escalate_or_alter_schema(roles, role, statement):
    with pytest.raises(DBAPIError), roles[role].begin() as connection:
        connection.execute(text(statement))


@pytest.mark.parametrize("role", ["iam_permissions", "iam_sync", "iam_audit", "iam_dispatcher"])
@pytest.mark.parametrize("table", ["credenciales", "mfa_totp"])
def test_unrelated_service_cannot_read_credentials_or_mfa(roles, role, table):
    with pytest.raises(DBAPIError), roles[role].begin() as connection:
        connection.execute(text(f"SELECT * FROM {table}"))


@pytest.mark.parametrize("role,statement", [
    ("iam_permissions", "UPDATE usuarios_plataforma SET activo=FALSE WHERE id=2"),
    ("iam_sync", "UPDATE sync_jobs SET usuario_id=2"),
    ("iam_dispatcher", "UPDATE auditoria_outbox SET detalle='{}'::jsonb"),
    ("iam_dispatcher", "DELETE FROM auditoria_outbox"),
    ("iam_identity", "UPDATE sync_jobs SET estado='COMPLETADO'"),
    ("iam_identity", "UPDATE auditoria_outbox SET estado='COMPLETADO'"),
    ("iam_audit", "UPDATE auditoria_eventos SET resultado='EXITO'"),
    ("iam_audit", "DELETE FROM auditoria_eventos"),
    ("iam_backup", "UPDATE usuarios_plataforma SET activo=FALSE WHERE id=2"),
    ("iam_identity", "SELECT detalle FROM auditoria_outbox"),
    ("iam_permissions", "SELECT detalle FROM auditoria_outbox"),
    ("iam_identity", "INSERT INTO auditoria_outbox(evento_uuid,fecha_evento,servicio,evento,resultado,estado) VALUES (gen_random_uuid(),NOW(),'fixture','FORGED','EXITO','COMPLETADO')"),
])
def test_runtime_cannot_modify_foreign_security_data(roles, role, statement):
    with pytest.raises(DBAPIError), roles[role].begin() as connection:
        connection.execute(text(statement))


def test_permissions_locks_do_not_require_identity_write_grants(roles):
    with roles["iam_permissions"].begin() as connection:
        assert connection.execute(text("SELECT id FROM public.iam_lock_active_user(2)")).scalar_one() == 2
        assert connection.execute(text("SELECT id FROM public.iam_lock_memberships(2,1)")).scalar_one() == 1
        assert connection.execute(text("SELECT id FROM public.iam_lock_memberships(2,2)")).all() == []
        assert connection.execute(text("SELECT id FROM public.iam_lock_active_user(-1)")).all() == []


def test_workers_can_change_delivery_state_but_not_payload(roles, db):
    with db.begin() as connection:
        job_id = connection.execute(text("""
            INSERT INTO sync_jobs(operacion, usuario_id, compania_id, solicitado_por_usuario_id)
            VALUES ('PROVISIONAR',2,1,1) RETURNING id
        """)).scalar_one()
        audit_id = connection.execute(text("""
            INSERT INTO auditoria_outbox(evento_uuid,fecha_evento,servicio,evento,resultado)
            VALUES (:uuid,NOW(),'fixture','ROLE_FIXTURE','EXITO') RETURNING id
        """), {"uuid": str(uuid4())}).scalar_one()
    with roles["iam_sync"].begin() as connection:
        assert connection.execute(text("UPDATE sync_jobs SET estado='PROCESANDO',intentos=1 WHERE id=:id"),
                                  {"id": job_id}).rowcount == 1
    with roles["iam_dispatcher"].begin() as connection:
        assert connection.execute(text("UPDATE auditoria_outbox SET estado='PROCESANDO',intentos=1 WHERE id=:id"),
                                  {"id": audit_id}).rowcount == 1


def test_identity_reset_works_without_superuser(roles, db, headers, challenge, monkeypatch):
    auth = headers(1)
    headers(2)
    challenge(2)
    # Every imported Identity DB user switches to the restricted real login.
    for module in list(sys.modules.values()):
        if getattr(module, "engine", None) is admin_engine:
            monkeypatch.setattr(module, "engine", roles["iam_identity"])
    with TestClient(main.app) as client:
        response = client.post("/auth/usuarios/2/mfa/restablecer", headers=auth)
    assert response.status_code == 200, response.text
    with db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM auditoria_outbox WHERE evento='MFA_RESTABLECIDO_ADMIN'")).scalar_one() == 1


def test_audit_insert_and_read_only_backup_are_allowed(roles):
    with roles["iam_audit"].begin() as connection:
        connection.execute(text("""
            INSERT INTO auditoria_eventos(evento_uuid,fecha_evento,servicio,evento,resultado)
            VALUES (:uuid,:date,'fixture','ROLE_FIXTURE','EXITO')
        """), {"uuid": str(uuid4()), "date": datetime.now(timezone.utc)})
    with roles["iam_backup"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM auditoria_eventos WHERE evento='ROLE_FIXTURE'")).scalar_one() >= 1
