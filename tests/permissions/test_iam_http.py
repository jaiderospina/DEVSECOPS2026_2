"""Integra las API reales por HTTP y PostgreSQL; sesión de prueba, no login/TOTP real."""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import httpx
import jwt
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import text
import main

def test_real_iam_session_revocation_expiry_and_password_gate(db):
    signing_key = os.environ["IAM_TEST_JWT_SECRET"]
    mfa_key = Fernet.generate_key()
    encrypted_fixture = Fernet(mfa_key).encrypt(b"fixture-not-a-real-totp-secret").decode()
    jti = str(uuid4())
    with db.begin() as c:
        c.execute(text("""
            INSERT INTO credenciales(usuario_id, password_hash, password_expira_en)
            VALUES (1, 'fixture-not-used-for-password-authentication', NOW() + INTERVAL '1 day')
        """))
        c.execute(text("""
            INSERT INTO mfa_totp(usuario_id, secreto_cifrado, activo)
            VALUES (1, :cipher, TRUE)
        """), {"cipher": encrypted_fixture})
        c.execute(text("""
            INSERT INTO sesiones(usuario_id, jti, fecha_expiracion)
            VALUES (1, :jti, NOW() + INTERVAL '1 hour')
        """), {"jti": jti})
    identity = Path(__file__).resolve().parents[2] / "servicios/identity-service"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "18003"],
        cwd=identity, env={**os.environ, "JWT_SECRET": signing_key, "JWT_ALGORITHM": "HS256",
                          "MFA_ENCRYPTION_KEY": mfa_key.decode()},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        ready = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError("Identity no arrancó en el entorno efímero")
            try:
                ready = httpx.get("http://127.0.0.1:18003/", timeout=1).status_code == 200
                if ready:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        assert ready, "Identity no respondió en el entorno efímero"
        payload = {"sub": "1", "jti": jti, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, signing_key, algorithm="HS256")
        with TestClient(main.app) as client:
            headers = {"Authorization": "Bearer " + token}
            assert client.get("/v1/companies", headers=headers).status_code == 200
            with db.begin() as c:
                c.execute(text("UPDATE sesiones SET revocada = TRUE, fecha_revocacion = NOW() WHERE usuario_id = 1"))
            assert client.get("/v1/companies", headers=headers).status_code == 401
            with db.begin() as c:
                c.execute(text("UPDATE sesiones SET revocada = FALSE, fecha_revocacion = NULL WHERE usuario_id = 1"))
                c.execute(text("UPDATE credenciales SET requiere_cambio_password = TRUE WHERE usuario_id = 1"))
            assert client.get("/v1/companies", headers=headers).status_code == 403
            expired = jwt.encode({**payload, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, signing_key, algorithm="HS256")
            assert client.get("/v1/companies", headers={"Authorization": "Bearer " + expired}).status_code == 401
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
