"""PostgreSQL efímero de CI. Nunca importar configuración ni datos del PC."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "servicios/permissions-service"))
import main
from auth import Actor, get_actor

@pytest.fixture
def db():
    with main.engine.begin() as c:
        c.execute(text("TRUNCATE auditoria_outbox, usuarios_plataforma, companias RESTART IDENTITY CASCADE"))
        for uid, name in [(1, "Soporte A"), (2, "Lider A"), (3, "Lider B"), (4, "Soporte B"), (5, "Admin TI")]:
            c.execute(text("""
                INSERT INTO usuarios_plataforma(id, nombre, email)
                VALUES (:id, :name, :email)
            """), {"id": uid, "name": name, "email": "usuario" + str(uid) + "@example.org"})
        c.execute(text("INSERT INTO companias(id, codigo, nombre) VALUES (1, 'A', 'Compañía A'), (2, 'B', 'Compañía B')"))
        for uid, role in [(1, "ADMIN_SOPORTE"), (2, "LIDER_FACTURACION"), (3, "LIDER_FACTURACION"), (4, "ADMIN_SOPORTE"), (5, "ADMIN_TI")]:
            c.execute(text("""
                INSERT INTO usuario_roles_plataforma(usuario_id, rol_id)
                SELECT :uid, id FROM roles_plataforma WHERE nombre = :role
            """), {"uid": uid, "role": role})
        for uid, cid in [(1, 1), (2, 1), (3, 2), (4, 2)]:
            c.execute(text("INSERT INTO usuario_companias_plataforma(usuario_id, compania_id) VALUES (:uid, :cid)"),
                      {"uid": uid, "cid": cid})
    yield main.engine

@pytest.fixture
def as_user(db):
    clients = []
    def create(uid):
        main.app.dependency_overrides[get_actor] = lambda: Actor(uid)
        client = TestClient(main.app)
        clients.append(client)
        return client
    yield create
    main.app.dependency_overrides.clear()
    for client in clients:
        client.close()
