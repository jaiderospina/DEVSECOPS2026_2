"""Fixtures efímeras: JWT válido y PostgreSQL real; correo simulado, sin SMTP externo."""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import jwt
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import text

os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["MFA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "servicios/identity-service"))
import main
from database import engine
import usuarios
import cargas_usuarios
from cargas_excel import HEADERS

@pytest.fixture
def db():
    with engine.begin() as c:
        c.execute(text("TRUNCATE auditoria_outbox, usuarios_plataforma, companias RESTART IDENTITY CASCADE"))
        c.execute(text("UPDATE roles_plataforma SET activo = TRUE"))
        c.execute(text("INSERT INTO companias(id,codigo,nombre) VALUES (1,'A','Compañía A'),(2,'B','Compañía B')"))
        for uid, role, company in [(1,"ADMIN_SOPORTE",1),(2,"LIDER_FACTURACION",1),(3,"ADMIN_SOPORTE",2),(4,"ADMIN_TI",None)]:
            c.execute(text("INSERT INTO usuarios_plataforma(id,id_externo,nombre,email) VALUES (:uid,:ext,:name,:email)"),
                      {"uid":uid,"ext":"fixture-"+str(uid),"name":"Usuario "+str(uid),"email":"usuario"+str(uid)+"@example.org"})
            c.execute(text("INSERT INTO credenciales(usuario_id,password_hash,password_expira_en) VALUES (:uid,'fixture-not-for-login',NOW()+INTERVAL '1 day')"),{"uid":uid})
            c.execute(text("INSERT INTO mfa_totp(usuario_id,secreto_cifrado,activo) VALUES (:uid,'fixture-not-for-totp',TRUE)"),{"uid":uid})
            c.execute(text("INSERT INTO usuario_roles_plataforma(usuario_id,rol_id) SELECT :uid,id FROM roles_plataforma WHERE nombre=:role"),{"uid":uid,"role":role})
            if company:
                c.execute(text("INSERT INTO usuario_companias_plataforma(usuario_id,compania_id) VALUES (:uid,:cid)"),{"uid":uid,"cid":company})
        c.execute(text("SELECT setval(pg_get_serial_sequence('usuarios_plataforma','id'),4)"))
    yield engine

@pytest.fixture
def mail(monkeypatch):
    delivered = []
    # No capturar ni devolver contraseña temporal. Solo contar el destinatario ficticio.
    monkeypatch.setattr(usuarios,"enviar_password_temporal",lambda **kw: delivered.append(kw["destinatario"]))
    monkeypatch.setattr(cargas_usuarios,"validar_configuracion_correo",lambda: None)
    return delivered

@pytest.fixture
def client(db,mail):
    with TestClient(main.app) as c:
        yield c

@pytest.fixture
def headers(db):
    def create(uid=1):
        jti=str(uuid4())
        with db.begin() as c:
            c.execute(text("INSERT INTO sesiones(usuario_id,jti,fecha_expiracion) VALUES (:uid,:jti,NOW()+INTERVAL '1 hour')"),{"uid":uid,"jti":jti})
        token=jwt.encode({"sub":str(uid),"jti":jti,"exp":datetime.now(timezone.utc)+timedelta(hours=1)},os.environ["JWT_SECRET"],algorithm="HS256")
        return {"Authorization":"Bearer "+token}
    return create

@pytest.fixture
def excel():
    def create(rows=None,headers=HEADERS,title="Usuarios"):
        w=Workbook(); s=w.active; s.title=title
        s.append(list(headers))
        for row in rows or [("001","Persona Prueba","nueva@example.org","LIDER_FACTURACION")]:
            s.append(list(row))
        out=BytesIO(); w.save(out); w.close()
        return out.getvalue()
    return create

@pytest.fixture
def preview(client,headers,excel):
    def create(rows=None,company=1,auth=None):
        h=auth or headers()
        response=client.post("/usuarios/cargas/validar",headers=h,data={"compania_id":str(company)},
                             files={"archivo":("usuarios.xlsx",excel(rows),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert response.status_code==201,response.text
        return h,response.json()
    return create
