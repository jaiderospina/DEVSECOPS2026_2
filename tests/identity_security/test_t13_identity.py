"""T13: exercise public Identity routes, not the shared validator alone."""
import pytest
from sqlalchemy import text

# Distinct route implementations must each enforce the same boundary.
OPERATIONS = [
    ("GET", "/usuarios/{id}", None),
    ("PUT", "/usuarios/{id}", {"id_externo":"changed","nombre":"Changed Name","email":"changed@example.org"}),
    ("PATCH", "/usuarios/{id}/estado", {"activo":False}),
    ("PUT", "/auth/credenciales/{id}/reset-password", None),
    ("POST", "/auth/usuarios/{id}/sesiones/revocar", None),
    ("POST", "/auth/usuarios/{id}/desbloquear", None),
]
BOUNDARIES = [(4,2), (4,6), (1,4), (1,3), (1,5), (2,5), (7,5), (8,5)]

@pytest.mark.parametrize("actor,target", BOUNDARIES)
@pytest.mark.parametrize("method,path,payload", OPERATIONS)
def test_forbidden_administration(client, headers, denied, actor, target, method, path, payload):
    auth = headers(actor)
    denied(lambda: client.request(method, path.format(id=target), headers=auth,
                                  **({"json":payload} if payload is not None else {})), 403)

@pytest.mark.parametrize("actor,target", [(1,4),(1,3),(1,5),(2,5),(7,5),(8,5)])
def test_role_change_forbidden_target(client, headers, denied, actor, target):
    auth = headers(actor)
    denied(lambda: client.patch(f"/usuarios/{target}/rol", headers=auth,
                                json={"rol":"LIDER_LOGISTICA"}),403)

@pytest.mark.parametrize("role", ["ADMIN_TI","ADMIN_SOPORTE"])
def test_support_cannot_assign_administrative_role(client,headers,denied,role):
    auth=headers(1)
    denied(lambda:client.patch("/usuarios/2/rol",headers=auth,json={"rol":role}),422)

@pytest.mark.parametrize("role,company,status", [("ADMIN_TI",1,422),("ADMIN_SOPORTE",1,403),("LIDER_FACTURACION",2,403)])
def test_support_cannot_create_admin_or_foreign_leader(client,headers,denied,role,company,status):
    auth=headers(1)
    denied(lambda:client.post("/usuarios/identidad",headers=auth,json={
        "id_externo":"new-fixture","nombre":"New Fixture","email":"new@example.org",
        "rol":role,"compania_id":company}),status)

CHANGES = [
    "DELETE FROM usuario_companias_plataforma WHERE usuario_id=1",
    "UPDATE companias SET activo=FALSE WHERE id=1",
    "DELETE FROM usuario_roles_plataforma WHERE usuario_id=1",
]

@pytest.mark.parametrize("change",CHANGES)
@pytest.mark.parametrize("method,path,payload",OPERATIONS[:2])
def test_same_token_loses_scope_immediately(client,headers,db,denied,change,method,path,payload):
    auth=headers(1)
    # Prove the exact token worked, including the representative write.
    assert client.request(method,path.format(id=2),headers=auth,
                          **({"json":payload} if payload is not None else {})).status_code==200
    with db.begin() as c:c.execute(text(change))
    denied(lambda:client.request(method,path.format(id=2),headers=auth,
                                 **({"json":payload} if payload is not None else {})),403)

@pytest.mark.parametrize("actor,target",[(4,1),(1,2)])
def test_authorized_hierarchy_controls(client,headers,actor,target):
    auth=headers(actor)
    assert client.get(f"/usuarios/{target}",headers=auth).status_code==200
    assert client.put(f"/usuarios/{target}",headers=auth,json={
        "id_externo":f"fixture-{target}","nombre":"Allowed Change",
        "email":f"person{target}@example.org"}).status_code==200

@pytest.mark.parametrize("actor,expected",[(4,{1,3}),(1,{2,7,8})])
def test_user_list_does_not_disclose_foreign_identities(client,headers,actor,expected):
    response=client.get("/usuarios",headers=headers(actor))
    assert response.status_code==200
    assert {u["id"] for u in response.json()["usuarios"]}==expected

# Company management is a separate administrative boundary.
@pytest.mark.parametrize("actor",[1,2,7,8])
@pytest.mark.parametrize("method,path,payload",[
    ("POST","/companias",{"codigo":"NEW","nombre":"New Company"}),
    ("PUT","/companias/1",{"codigo":"A","nombre":"Changed Company"}),
    ("PATCH","/companias/1/estado",{"activo":False}),
    ("POST","/companias/asignaciones",{"usuario_id":3,"compania_id":1}),
    ("GET","/companias/asignaciones",None),
])
def test_non_ti_cannot_manage_companies(client,headers,denied,actor,method,path,payload):
    auth=headers(actor)
    denied(lambda:client.request(method,path,headers=auth,
                                 **({"json":payload} if payload is not None else {})),403)

@pytest.mark.parametrize("actor,path",[(1,"/companias/2/contexto"),(1,"/companias/2/usuarios"),(4,"/companias/1/usuarios")])
def test_company_context_and_identities_are_scoped(client,headers,denied,actor,path):
    auth=headers(actor)
    denied(lambda:client.get(path,headers=auth),403)
