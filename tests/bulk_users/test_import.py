from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text
from fastapi.testclient import TestClient
import main
import usuarios
import cargas_usuarios

def scalar(db,query,**params):
    with db.connect() as c:return c.execute(text(query),params).scalar_one()

def confirm(client,h,job):
    response=client.post("/usuarios/cargas/"+job["id"]+"/confirmar",headers=h,json={"confirmar":True})
    assert response.status_code==200,response.text

def row(client,h,job):
    return client.post("/usuarios/cargas/"+job["id"]+"/filas/2",headers=h)

def test_preview_creates_no_account_or_email_and_requires_consent(preview,client,db,mail):
    h,job=preview()
    assert job["compania"]["nombre"]=="Compañía A" and job["resumen"]["pendiente"]==1
    assert scalar(db,"SELECT count(*) FROM usuarios_plataforma")==4 and mail==[]
    assert row(client,h,job).status_code==409
    assert client.post("/usuarios/cargas/"+job["id"]+"/confirmar",headers=h,json={"confirmar":False}).status_code==400
    assert client.post("/usuarios/cargas/"+job["id"]+"/confirmar",headers=h,json={"confirmar":"true"}).status_code==422

def test_creation_atomic_role_company_credential_queue_audit_and_initial_views(preview,client,db,mail):
    h,job=preview();confirm(client,h,job)
    result=row(client,h,job);assert result.status_code==200,result.text
    data=result.json()["fila"];assert data["estado"]=="CREADA"
    uid=data["usuario_id"]
    with db.connect() as c:
        cred=c.execute(text("SELECT requiere_cambio_password,password_temporal_expira_en>NOW() AS vigente,password_hash LIKE '$argon2id$%' AS argon FROM credenciales WHERE usuario_id=:uid"),{"uid":uid}).mappings().one()
        assert all(cred.values())
    assert scalar(db,"SELECT compania_id FROM usuario_companias_plataforma WHERE usuario_id=:uid",uid=uid)==1
    assert scalar(db,"SELECT r.nombre FROM usuario_roles_plataforma ur JOIN roles_plataforma r ON r.id=ur.rol_id WHERE ur.usuario_id=:uid",uid=uid)=="LIDER_FACTURACION"
    assert scalar(db,"SELECT count(*) FROM sync_jobs WHERE usuario_id=:uid",uid=uid)==1
    assert scalar(db,"SELECT count(*) FROM auditoria_outbox WHERE evento='USUARIO_CREADO' AND objetivo_usuario_id=:uid",uid=uid)==1
    assert scalar(db,"SELECT count(*) FROM mfa_totp WHERE usuario_id=:uid",uid=uid)==0
    assert mail==["nueva@example.org"]
    assert not any(s in result.text for s in ("password_hash","password_temporal","secreto_cifrado","Bearer "))
    assert scalar(db,"SELECT count(*) FROM permisos_usuario_compania WHERE usuario_id=:uid AND compania_id=1 AND habilitado AND version=1 AND modificado_por=1",uid=uid)==3
    assert scalar(db,"SELECT count(*) FROM permisos_usuario_compania WHERE usuario_id=:uid AND codigo NOT LIKE 'facturacion.%'",uid=uid)==0
    with db.connect() as c:
        detail=c.execute(text("SELECT detalle FROM auditoria_outbox WHERE evento='USUARIO_CREADO' AND objetivo_usuario_id=:uid"),{"uid":uid}).scalar_one()
    assert set(detail["vistas_iniciales_habilitadas"])=={"facturacion.aprobaciones.consultar","facturacion.pagos.consultar","facturacion.impuestos.consultar"}

def test_idempotent_retry_does_not_create_or_send_again(preview,client,db,mail):
    h,job=preview();confirm(client,h,job)
    assert row(client,h,job).json()["fila"]["estado"]=="CREADA"
    assert row(client,h,job).json()["fila"]["estado"]=="CREADA"
    assert scalar(db,"SELECT count(*) FROM usuarios_plataforma WHERE id_externo='001'")==1
    assert len(mail)==1

def test_concurrent_row_requests_create_once(preview,client,db,mail):
    h,job=preview();confirm(client,h,job)
    def process(_):
        with TestClient(main.app) as other:return row(other,h,job)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(process,range(2)))
    assert all(r.status_code==200 and r.json()["fila"]["estado"]=="CREADA" for r in results)
    assert len(mail)==1
    assert scalar(db,"SELECT count(*) FROM usuarios_plataforma WHERE id_externo='001'")==1

def test_smtp_failure_rolls_back_user_queue_and_success_audit(preview,client,db,mail,monkeypatch):
    h,job=preview();confirm(client,h,job)
    def fail(**kw):raise RuntimeError("sensitive-fixture-not-to-return")
    monkeypatch.setattr(usuarios,"enviar_password_temporal",fail)
    result=row(client,h,job)
    assert result.status_code==200 and result.json()["fila"]["estado"]=="ERROR"
    assert "sensitive-fixture-not-to-return" not in result.text
    assert scalar(db,"SELECT count(*) FROM usuarios_plataforma")==4
    assert scalar(db,"SELECT count(*) FROM sync_jobs")==0
    assert scalar(db,"SELECT count(*) FROM auditoria_outbox WHERE evento='USUARIO_CREADO'")==0
    assert scalar(db,"SELECT count(*) FROM permisos_usuario_compania")==0

def test_preexisting_identity_is_invalid_not_updated(preview,client,db,mail):
    h,job=preview([("fixture-2","Cambio no permitido","otro@example.org","LIDER_LOGISTICA")])
    assert job["filas"][0]["codigo"]=="YA_REGISTRADA"
    assert "usuario2@example.org" not in str(job)
    assert scalar(db,"SELECT nombre FROM usuarios_plataforma WHERE id=2")=="Usuario 2" and mail==[]

def test_resume_in_new_session(preview,client,headers):
    h,job=preview();confirm(client,h,job)
    new=headers()
    loaded=client.get("/usuarios/cargas/"+job["id"],headers=new)
    assert loaded.status_code==200 and loaded.json()["resumen"]["pendiente"]==1
    assert row(client,new,job).json()["fila"]["estado"]=="CREADA"

def test_single_creation_retains_existing_behavior(client,headers,db,mail):
    response=client.post("/usuarios/identidad",headers=headers(),json={"id_externo":"unica","nombre":"Persona Unica","email":"unica@example.org","rol":"LIDER_LOGISTICA","compania_id":1})
    assert response.status_code in (200,201),response.text
    assert len(mail)==1 and scalar(db,"SELECT count(*) FROM cargas_usuarios")==0
    uid=response.json()["usuario"]["id"]
    assert scalar(db,"SELECT count(*) FROM permisos_usuario_compania WHERE usuario_id=:uid AND compania_id=1 AND habilitado AND codigo LIKE 'logistica.%'",uid=uid)==3

def test_smtp_configuration_required_without_disclosing_exception(preview,client,db,monkeypatch):
    h,job=preview()
    def fail():raise RuntimeError("smtp-private-fixture")
    monkeypatch.setattr(cargas_usuarios,"validar_configuracion_correo",fail)
    r=client.post("/usuarios/cargas/"+job["id"]+"/confirmar",headers=h,json={"confirmar":True})
    assert r.status_code==503 and "smtp-private-fixture" not in r.text
    assert scalar(db,"SELECT estado FROM cargas_usuarios")=="VALIDADA"
