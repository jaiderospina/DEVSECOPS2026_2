"""T15: both public routes retain their different existing contracts."""
import httpx
import pytest
import pyotp
from sqlalchemy import text
from conftest import PASSWORD
from mfa import descifrar_secreto_totp

AUTH="/auth/usuarios/{id}/mfa/restablecer"
USERS="/usuarios/{id}/mfa/restablecer"
COMMON=[(2,5,403),(7,5,403),(8,5,403),(1,4,403),(1,3,403),
        (1,5,403),(1,1,400)]
NEGATIVE=[(route,actor,target,status) for route in (AUTH,USERS) for actor,target,status in COMMON]
NEGATIVE += [(AUTH,4,2,403),(AUTH,4,6,403),(AUTH,4,4,400),(USERS,4,3,403)]

@pytest.mark.parametrize("route,actor,target,status",NEGATIVE)
def test_reset_forbidden_hierarchy(client,headers,denied,route,actor,target,status):
    auth=headers(actor)
    denied(lambda:client.post(route.format(id=target),headers=auth),status)

@pytest.mark.parametrize("route",[AUTH,USERS])
@pytest.mark.parametrize("change",[
    "DELETE FROM usuario_companias_plataforma WHERE usuario_id=1",
    "UPDATE companias SET activo=FALSE WHERE id=1",
])
def test_reset_loses_company_authority(client,headers,db,denied,route,change):
    auth=headers(1)
    assert client.get("/usuarios/2",headers=auth).status_code==200
    with db.begin() as c:c.execute(text(change))
    denied(lambda:client.post(route.format(id=2),headers=auth),403)

@pytest.mark.parametrize("route,actor,target",[(AUTH,4,1),(AUTH,1,2),(USERS,1,2)])
def test_reset_revokes_and_requires_fresh_enrolment(client,headers,db,snapshot,challenge,permissions_url,route,actor,target):
    admin=headers(actor)
    old_tokens=[headers(target),headers(target)]
    other_token=headers(5)
    old_challenges=[challenge(target),challenge(target)]
    challenge(5)
    unrelated=snapshot(5)
    with db.connect() as c:
        previous_cipher=c.execute(text("SELECT secreto_cifrado FROM mfa_totp WHERE usuario_id=:id"),dict(id=target)).scalar_one()
        session_ids=set(c.execute(text("SELECT id FROM sesiones WHERE usuario_id=:id AND revocada=FALSE AND fecha_expiracion>NOW()"),dict(id=target)).scalars())
    assert len(session_ids)==2
    permission_path="/v1/companies" if target==1 else "/v1/me/permissions"
    # Prove the old token crossed the real Permissions/IAM boundary before reset.
    assert httpx.get(permissions_url+permission_path,headers=old_tokens[0],trust_env=False).status_code==200
    response=client.post(route.format(id=target),headers=admin)
    assert response.status_code==200,response.text
    assert response.json()["sesiones_revocadas"]==2
    assert "secreto" not in response.text and "otpauth" not in response.text and "access_token" not in response.text
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM mfa_totp WHERE usuario_id=:id"),dict(id=target)).scalar_one()==0
        rows=c.execute(text("SELECT id,revocada,fecha_revocacion FROM sesiones WHERE usuario_id=:id"),dict(id=target)).mappings().all()
        assert {r["id"] for r in rows}==session_ids
        assert all(r["revocada"] and r["fecha_revocacion"] is not None for r in rows)
        challenges=c.execute(text("SELECT usado,usado_en FROM mfa_desafios WHERE usuario_id=:id"),dict(id=target)).mappings().all()
        assert len(challenges)==2
        assert all(r["usado"] and r["usado_en"] is not None for r in challenges)
    assert snapshot(5)==unrelated
    for token in old_tokens:
        assert client.get("/auth/me",headers=token).status_code==401
    assert httpx.get(permissions_url+permission_path,headers=old_tokens[0],trust_env=False).status_code==401
    for old in old_challenges:
        assert client.post("/auth/mfa/verificar-login",json={"desafio":old,"codigo":"123456"}).status_code==401
        assert client.post("/auth/mfa/enrolamiento-obligatorio",json={"desafio":old}).status_code==401
    assert client.get("/auth/me",headers=other_token).status_code==200
    login=client.post("/auth/login",json={"email":f"person{target}@example.org","password":PASSWORD})
    assert login.status_code==200,login.text
    body=login.json()
    assert body["mfa_requerido"] is True and body["mfa_enrolamiento_requerido"] is True
    assert "access_token" not in body and "refresh_token" not in body
    with db.connect() as c:
        assert set(c.execute(text("SELECT id FROM sesiones WHERE usuario_id=:id"),dict(id=target)).scalars())==session_ids
    # A fresh first-factor challenge can enrol, but still cannot create a session.
    qr=client.post("/auth/mfa/enrolamiento-obligatorio",json={"desafio":body["desafio_mfa"]})
    assert qr.status_code==200 and qr.headers["content-type"]=="image/png"
    with db.connect() as c:
        enrolled=c.execute(text("SELECT secreto_cifrado,activo FROM mfa_totp WHERE usuario_id=:id"),dict(id=target)).mappings().one()
        new_secret=descifrar_secreto_totp(enrolled["secreto_cifrado"])
        assert new_secret!=descifrar_secreto_totp(previous_cipher)
        assert enrolled["activo"] is False
        assert set(c.execute(text("SELECT id FROM sesiones WHERE usuario_id=:id"),dict(id=target)).scalars())==session_ids
    # Only possession of the newly enrolled TOTP completes authentication.
    activated=client.post("/auth/mfa/activar-obligatorio",json={
        "desafio":body["desafio_mfa"],"codigo":pyotp.TOTP(new_secret).now()})
    assert activated.status_code==200,activated.text
    new_token=activated.json()["access_token"]
    assert client.get("/auth/me",headers={"Authorization":"Bearer "+new_token}).status_code==200
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM sesiones WHERE usuario_id=:id AND revocada=FALSE"),dict(id=target)).scalar_one()==1
    assert snapshot(5)==unrelated

@pytest.mark.parametrize("route,status",[(AUTH,200),(USERS,409)])
def test_existing_contract_without_mfa(client,headers,db,denied,route,status):
    auth=headers(1)
    with db.begin() as c:c.execute(text("DELETE FROM mfa_totp WHERE usuario_id=2"))
    if status==409:
        denied(lambda:client.post(route.format(id=2),headers=auth),409)
    else:
        response=client.post(route.format(id=2),headers=auth)
        assert response.status_code==200
        assert response.json()["mfa_activo"] is False

@pytest.mark.parametrize("route",[AUTH,USERS])
def test_inactive_target_is_rejected(client,headers,db,denied,route):
    auth=headers(1)
    with db.begin() as c:c.execute(text("UPDATE usuarios_plataforma SET activo=FALSE WHERE id=2"))
    denied(lambda:client.post(route.format(id=2),headers=auth),400)
