"""Política inicial solicitada: tres vistas de su área, sin reactivar ajustes posteriores."""
import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import text
from permisos_iniciales import VISTAS_POR_ROL

EXPECTED = {
    "LIDER_FACTURACION": {"facturacion.aprobaciones.consultar","facturacion.pagos.consultar","facturacion.impuestos.consultar"},
    "LIDER_LOGISTICA": {"logistica.despachos.consultar","logistica.entregas.consultar","logistica.inventario.consultar"},
    "LIDER_GESTION_HUMANA": {"gestion_humana.colaboradores.consultar","gestion_humana.novedades.consultar","gestion_humana.vacaciones.consultar"},
}

def test_initial_views_match_permissions_api_catalog():
    path=Path(__file__).resolve().parents[2]/"servicios/permissions-service/catalog.py"
    spec=importlib.util.spec_from_file_location("catalog_contract",path)
    catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
    for role,expected in EXPECTED.items():
        assert set(VISTAS_POR_ROL[role])==expected
        assert expected=={code for code,data in catalog.PERMISSIONS.items() if data["rol"]==role}

@pytest.mark.parametrize("role",list(EXPECTED))
def test_bulk_leader_receives_exactly_its_three_views(preview,client,db,role):
    h,job=preview([("100","Persona Prueba","rol@example.org",role)])
    prefix="/usuarios/cargas/"+job["id"]
    assert client.post(prefix+"/confirmar",headers=h,json={"confirmar":True}).status_code==200
    r=client.post(prefix+"/filas/2",headers=h)
    assert r.status_code==200 and r.json()["fila"]["estado"]=="CREADA"
    uid=r.json()["fila"]["usuario_id"]
    with db.connect() as c:
        grants=c.execute(text("SELECT codigo,habilitado,compania_id FROM permisos_usuario_compania WHERE usuario_id=:uid"),{"uid":uid}).mappings().all()
    assert {g["codigo"] for g in grants}==EXPECTED[role]
    assert all(g["habilitado"] and g["compania_id"]==1 for g in grants)

def test_retry_and_duplicate_upload_preserve_disabled_view(preview,client,db,mail):
    h,job=preview()
    prefix="/usuarios/cargas/"+job["id"]
    client.post(prefix+"/confirmar",headers=h,json={"confirmar":True})
    uid=client.post(prefix+"/filas/2",headers=h).json()["fila"]["usuario_id"]
    with db.begin() as c:
        c.execute(text("UPDATE permisos_usuario_compania SET habilitado=FALSE,version=version+1 WHERE usuario_id=:uid AND codigo='facturacion.pagos.consultar'"),{"uid":uid})
    assert client.post(prefix+"/filas/2",headers=h).json()["fila"]["estado"]=="CREADA"
    _,duplicate=preview(auth=h)
    assert duplicate["filas"][0]["codigo"]=="YA_REGISTRADA"
    with db.connect() as c:
        grant=c.execute(text("SELECT habilitado,version FROM permisos_usuario_compania WHERE usuario_id=:uid AND codigo='facturacion.pagos.consultar'"),{"uid":uid}).one()
    assert tuple(grant)==(False,2) and len(mail)==1

def test_admin_support_creation_receives_no_leader_views(client,headers,db):
    r=client.post("/usuarios/identidad",headers=headers(4),json={
        "id_externo":"support-new","nombre":"Soporte Nuevo","email":"soporte-nuevo@example.org","rol":"ADMIN_SOPORTE"})
    assert r.status_code==201,r.text
    uid=r.json()["usuario"]["id"]
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM permisos_usuario_compania WHERE usuario_id=:uid"),{"uid":uid}).scalar_one()==0

def test_rejected_batch_leaves_existing_disabled_permissions_untouched(preview,db):
    with db.begin() as c:
        c.execute(text("INSERT INTO permisos_usuario_compania(usuario_id,compania_id,codigo,habilitado,version) VALUES (2,1,'facturacion.pagos.consultar',FALSE,7)"))
    _,job=preview([("fixture-2","Duplicada","duplicada@example.org","LIDER_FACTURACION")])
    assert job["filas"][0]["codigo"]=="YA_REGISTRADA"
    with db.connect() as c:
        grant=c.execute(text("SELECT habilitado,version FROM permisos_usuario_compania WHERE usuario_id=2")).one()
    assert tuple(grant)==(False,7)
