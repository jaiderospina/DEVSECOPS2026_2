"""Isolated PostgreSQL + real Identity dependencies; never use workstation data.
Run separately from permissions/bulk_users (their modules share import names).
"""
import hashlib
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pyotp
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import text

if (os.environ.get("DB_NAME") != "iam_negative_test"
        or os.environ.get("DB_HOST") != "127.0.0.1"
        or os.environ.get("IAM_NEGATIVE_DISPOSABLE") != "1"):
    raise RuntimeError("Requires explicitly disposable local iam_negative_test database")
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["MFA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "servicios/identity-service"))
import main
import autenticacion
import usuarios
from database import engine
from mfa import cifrar_secreto_totp

PASSWORD = "FixtureOnly-StrongPassword-742!"
PEOPLE = [(1, "ADMIN_SOPORTE", 1), (2, "LIDER_FACTURACION", 1),
          (3, "ADMIN_SOPORTE", 2), (4, "ADMIN_TI", None),
          (5, "LIDER_FACTURACION", 2), (6, "ADMIN_TI", None),
          (7, "LIDER_LOGISTICA", 1), (8, "LIDER_GESTION_HUMANA", 1)]
TABLES = ("usuarios_plataforma", "credenciales", "roles_plataforma",
          "usuario_roles_plataforma", "companias", "usuario_companias_plataforma",
          "mfa_totp", "mfa_desafios", "sesiones", "sync_jobs",
          "permisos_usuario_compania", "cargas_usuarios", "cargas_usuario_filas")

@pytest.fixture
def db():
    password_hash = autenticacion.password_hasher.hash(PASSWORD)
    with engine.begin() as c:
        c.execute(text("TRUNCATE auditoria_outbox, usuarios_plataforma, companias RESTART IDENTITY CASCADE"))
        c.execute(text("UPDATE roles_plataforma SET activo=TRUE"))
        c.execute(text("INSERT INTO companias(id,codigo,nombre) VALUES (1,'A','Tenant A'),(2,'B','Tenant B')"))
        for uid, role, company in PEOPLE:
            c.execute(text("INSERT INTO usuarios_plataforma(id,id_externo,nombre,email) VALUES (:id,:ext,:name,:email)"),
                      dict(id=uid, ext=f"fixture-{uid}", name=f"Fixture Person {uid}", email=f"person{uid}@example.org"))
            c.execute(text("INSERT INTO credenciales(usuario_id,password_hash,password_expira_en) VALUES (:id,:hash,NOW()+INTERVAL '1 day')"), dict(id=uid, hash=password_hash))
            c.execute(text("INSERT INTO mfa_totp(usuario_id,secreto_cifrado,activo) VALUES (:id,:cipher,TRUE)"),
                      dict(id=uid, cipher=cifrar_secreto_totp(pyotp.random_base32())))
            c.execute(text("INSERT INTO usuario_roles_plataforma(usuario_id,rol_id) SELECT :id,id FROM roles_plataforma WHERE nombre=:role"), dict(id=uid, role=role))
            if company:
                c.execute(text("INSERT INTO usuario_companias_plataforma(usuario_id,compania_id) VALUES (:id,:company)"), dict(id=uid, company=company))
        c.execute(text("SELECT setval(pg_get_serial_sequence('usuarios_plataforma','id'),8)"))
    yield engine

@pytest.fixture
def client(db, monkeypatch):
    # SMTP is the only substituted external side effect; authorization is real.
    def forbidden_mail(**kwargs):
        pytest.fail("Denied administrative operation attempted SMTP delivery")
    monkeypatch.setattr(usuarios, "enviar_password_temporal", forbidden_mail)
    monkeypatch.setattr(autenticacion, "enviar_password_temporal", forbidden_mail)
    with TestClient(main.app) as client:
        yield client

@pytest.fixture
def headers(db):
    def create(uid=1):
        jti = str(uuid4())
        with db.begin() as c:
            c.execute(text("INSERT INTO sesiones(usuario_id,jti,fecha_expiracion) VALUES (:id,:jti,NOW()+INTERVAL '1 hour')"), dict(id=uid, jti=jti))
        token = jwt.encode(dict(sub=str(uid), jti=jti, exp=datetime.now(timezone.utc)+timedelta(hours=1)), os.environ["JWT_SECRET"], algorithm="HS256")
        return {"Authorization": "Bearer " + token}
    return create

@pytest.fixture
def snapshot(db):
    def read(uid=None):
        result = {}
        with db.connect() as c:
            for table in TABLES:
                # Identifiers are a fixed allowlist, never request input.
                rows = c.execute(text(f"SELECT to_jsonb(t) AS row FROM {table} t")).scalars().all()
                if uid is not None:
                    rows = [r for r in rows if r.get("usuario_id", r.get("id") if table == "usuarios_plataforma" else None) == uid]
                for row in rows:
                    if table == "sesiones":
                        # Authenticated requests legitimately update actor activity.
                        row.pop("ultima_actividad", None)
                result[table] = sorted(rows, key=lambda r: str(r))
        return result
    return read

@pytest.fixture
def denied(snapshot):
    def check(call, status):
        before = snapshot()
        response = call()
        assert response.status_code == status, response.text
        body = response.json()
        assert set(body) == {"detail"}
        if status == 422:
            assert isinstance(body["detail"], list)
            assert all("input" not in error for error in body["detail"])
        else:
            assert isinstance(body["detail"], str)
        assert not any(f"person{i}@example.org" in response.text or f"Fixture Person {i}" in response.text or f"fixture-{i}" in response.text for i in range(1,9))
        assert snapshot() == before, "Denied request changed protected persistent state"
        return response
    return check

@pytest.fixture
def challenge(db):
    def create(uid):
        value = secrets.token_urlsafe(32)
        with db.begin() as c:
            c.execute(text("INSERT INTO mfa_desafios(usuario_id,desafio_hash,fecha_expiracion) VALUES (:id,:hash,NOW()+INTERVAL '5 minutes')"), dict(id=uid, hash=hashlib.sha256(value.encode()).hexdigest()))
        return value
    return create

@pytest.fixture(scope="session")
def permissions_url():
    """Real Permissions -> Identity HTTP hop, separate processes/import namespaces."""
    import socket
    import subprocess
    import time
    import httpx
    repo = Path(__file__).resolve().parents[2]
    processes = []
    def start(service, extra):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0))
            port=sock.getsockname()[1]
        process=subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port",str(port)],
                                 cwd=repo/"servicios"/service,env={**os.environ,**extra},
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        processes.append(process)
        url=f"http://127.0.0.1:{port}"
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if process.poll() is not None:pytest.fail(f"{service} failed to start")
            try:
                if httpx.get(url+"/",timeout=1,trust_env=False).status_code==200:return url
            except httpx.HTTPError:pass
            time.sleep(.1)
        pytest.fail(f"{service} did not become ready")
    try:
        identity=start("identity-service",{})
        yield start("permissions-service",{"IAM_BASE_URL":identity})
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
