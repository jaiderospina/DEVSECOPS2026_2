"""Autorización real sobre PostgreSQL; el proveedor de sesión se dobla aquí."""
import json
from pathlib import Path
import pytest
from sqlalchemy import text
import main

CODE = "facturacion.pagos.consultar"
PATH = "/v1/companies/1/users/2/permissions/" + CODE

def set_permission(client, enabled=True, version=0, path=PATH):
    return client.put(path, json={"habilitado": enabled, "version": version})

def test_support_sees_only_assigned_company_and_leaders(as_user):
    client = as_user(1)
    assert [c["id"] for c in client.get("/v1/companies").json()["companias"]] == [1]
    grid = client.get("/v1/companies/1/permissions").json()
    assert [u["id"] for u in grid["usuarios"]] == [2]
    assert len(grid["usuarios"][0]["permisos"]) == 3
    assert all(not p["habilitado"] for p in grid["usuarios"][0]["permisos"])

def test_enable_disable_relogin_and_backend_denial(as_user, db):
    support = as_user(1)
    assert set_permission(support).json()["version"] == 1
    leader = as_user(2)
    assert leader.get("/v1/me/views/" + CODE).status_code == 200
    assert any(p["codigo"] == CODE and p["habilitado"] for p in leader.get("/v1/me/permissions").json()["permisos"])
    support = as_user(1)
    assert set_permission(support, False, 1).json()["version"] == 2
    # Una consulta nueva con el mismo usuario no depende de permisos guardados en JWT.
    leader = as_user(2)
    assert leader.get("/v1/me/views/" + CODE).status_code == 403
    assert not any(p["habilitado"] for p in leader.get("/v1/me/permissions").json()["permisos"])
    with db.connect() as c:
        event = c.execute(text("""
            SELECT detalle FROM auditoria_outbox WHERE servicio = 'permissions-service'
            AND objetivo_usuario_id = 2 ORDER BY id DESC LIMIT 1
        """)).scalar_one()
        assert event["habilitado_nuevo"] is False
        assert "password" not in json.dumps(event)

@pytest.mark.parametrize("uid", [2, 5])
def test_leader_and_admin_ti_cannot_manage_permissions(as_user, uid):
    client = as_user(uid)
    assert client.get("/v1/companies").status_code == 403
    assert set_permission(client).status_code == 403

@pytest.mark.parametrize("path", [
    "/v1/companies/2/users/3/permissions/" + CODE,
    "/v1/companies/1/users/3/permissions/" + CODE,
    "/v1/companies/1/users/1/permissions/" + CODE,
    "/v1/companies/1/users/2/permissions/logistica.entregas.consultar",
    "/v1/companies/1/users/2/permissions/no.existe",
])
def test_forged_company_target_or_permission_is_rejected(as_user, path):
    assert set_permission(as_user(1), path=path).status_code == 403

def test_foreign_company_grid_is_not_disclosed(as_user):
    assert as_user(1).get("/v1/companies/2/permissions").status_code == 403

def test_stale_update_cannot_overwrite_new_state(as_user):
    client = as_user(1)
    assert set_permission(client).status_code == 200
    assert set_permission(client, False, 0).status_code == 409
    assert set_permission(client, False, 1).status_code == 200

def test_role_and_membership_revocation_take_effect(as_user, db):
    client = as_user(1)
    assert set_permission(client).status_code == 200
    with db.begin() as c:
        c.execute(text("DELETE FROM usuario_companias_plataforma WHERE usuario_id = 1"))
    assert set_permission(client, False, 1).status_code == 403
    with db.begin() as c:
        c.execute(text("DELETE FROM usuario_roles_plataforma WHERE usuario_id = 2"))
    assert as_user(2).get("/v1/me/views/" + CODE).status_code == 403

def test_inactive_or_ambiguous_company_is_denied(as_user, db):
    with db.begin() as c:
        c.execute(text("INSERT INTO usuario_companias_plataforma(usuario_id, compania_id) VALUES (2, 2)"))
    assert set_permission(as_user(1)).status_code == 403
    with db.begin() as c:
        c.execute(text("DELETE FROM usuario_companias_plataforma WHERE usuario_id = 2 AND compania_id = 2"))
        c.execute(text("UPDATE companias SET activo = FALSE WHERE id = 1"))
    assert set_permission(as_user(1)).status_code == 403

@pytest.mark.parametrize("payload", [
    {"habilitado": "false", "version": 0},
    {"habilitado": True, "version": -1},
    {"habilitado": True, "version": 0, "rol": "ADMIN_TI"},
])
def test_strict_payload_without_echoing_inputs(as_user, payload):
    response = as_user(1).put(PATH, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Parámetros inválidos"}

def test_audit_failure_rolls_back_grant(as_user, db):
    client = as_user(1)
    # Forzar un fallo en Outbox en la misma transacción.
    with db.begin() as c:
        c.execute(text("""
            ALTER TABLE auditoria_outbox ADD CONSTRAINT reject_permission_event
            CHECK (servicio <> 'permissions-service')
        """))
    try:
        assert set_permission(client).status_code == 503
        with db.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM permisos_usuario_compania")).scalar_one() == 0
    finally:
        with db.begin() as c:
            c.execute(text("ALTER TABLE auditoria_outbox DROP CONSTRAINT reject_permission_event"))

def test_first_migration_preserves_existing_views_and_does_not_reenable(as_user, db):
    script = (Path(__file__).resolve().parents[2] / "postgres-init/11-create-permisos.sql").read_text()
    with db.begin() as c:
        c.execute(text("DELETE FROM permisos_migraciones"))
        c.exec_driver_sql(script)
    client = as_user(1)
    assert all(p["habilitado"] for p in client.get("/v1/companies/1/permissions").json()["usuarios"][0]["permisos"])
    assert set_permission(client, False, 1).status_code == 200
    with db.begin() as c:
        c.exec_driver_sql(script)
    permissions = client.get("/v1/companies/1/permissions").json()["usuarios"][0]["permisos"]
    assert next(p for p in permissions if p["codigo"] == CODE)["habilitado"] is False

def test_cors_preflight_preserves_security_headers(as_user):
    client = as_user(1)
    response = client.options(PATH, headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "Authorization,Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in client.get("/", headers={"Origin": "https://unknown.invalid"}).headers
