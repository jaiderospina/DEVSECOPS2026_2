"""API independiente de permisos con RBAC, alcance de compañía y Outbox atómica."""
import json
import os
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from auth import Actor, get_actor
from catalog import LEADER_ROLES, PERMISSIONS
from database import engine

app = FastAPI(title="IAM Secure Permissions API", version="1.0.0")
origins = [s.strip().rstrip("/") for s in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if s.strip()]
if not origins or "*" in origins:
    raise RuntimeError("Configure orígenes CORS explícitos")
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_methods=["GET", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Parámetros inválidos"})

@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={"detail": "Operación no disponible"})

class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")
    habilitado: StrictBool
    version: StrictInt = Field(ge=0)

def user_roles(connection, uid):
    user = connection.execute(text("""
        SELECT id, nombre, email FROM public.iam_lock_active_user(:uid)
    """), {"uid": uid}).mappings().first()
    if user is None:
        raise HTTPException(403, "Identidad no disponible")
    roles = set(connection.execute(text("""
        SELECT r.nombre FROM roles_plataforma r
        JOIN usuario_roles_plataforma ur ON ur.rol_id = r.id
        WHERE ur.usuario_id = :uid AND r.activo = TRUE
    """), {"uid": uid}).scalars())
    return user, roles

def support(connection, actor):
    user, roles = user_roles(connection, actor.id)
    if "ADMIN_SOPORTE" not in roles or "ADMIN_TI" in roles:
        raise HTTPException(403, "Acceso exclusivo para ADMIN_SOPORTE")
    return user

def support_company(connection, actor, company):
    support(connection, actor)
    row = connection.execute(text("""
        SELECT id, codigo, nombre FROM public.iam_lock_memberships(:uid, :cid)
    """), {"uid": actor.id, "cid": company}).mappings().first()
    if row is None:
        raise HTTPException(403, "Compañía fuera de su alcance")
    return dict(row)

def leader(connection, uid, company=None):
    user, roles = user_roles(connection, uid)
    if len(roles) != 1 or not roles.issubset(LEADER_ROLES):
        raise HTTPException(403, "Solo se administran permisos de líderes")
    companies = connection.execute(text("""
        SELECT id FROM public.iam_lock_memberships(:uid, NULL)
    """), {"uid": uid}).scalars().all()
    if len(companies) != 1 or (company is not None and companies[0] != company):
        raise HTTPException(403, "Compañía del usuario fuera de alcance o ambigua")
    return dict(user), next(iter(roles)), companies[0]

def grants(connection, uid, cid, role):
    stored = {
        r["codigo"]: r for r in connection.execute(text("""
            SELECT codigo, habilitado, version FROM permisos_usuario_compania
            WHERE usuario_id = :uid AND compania_id = :cid
        """), {"uid": uid, "cid": cid}).mappings()
    }
    return [
        {**item, "habilitado": bool(stored.get(code, {}).get("habilitado", False)),
         "version": stored.get(code, {}).get("version", 0)}
        for code, item in PERMISSIONS.items() if item["rol"] == role
    ]

@app.get("/")
def health():
    return {"servicio": "permissions", "estado": "funcionando"}

@app.get("/v1/companies")
def companies(actor: Actor = Depends(get_actor)):
    with engine.begin() as connection:
        support(connection, actor)
        rows = connection.execute(text("""
            SELECT c.id, c.codigo, c.nombre FROM companias c
            JOIN usuario_companias_plataforma uc ON uc.compania_id = c.id
            WHERE uc.usuario_id = :uid AND c.activo = TRUE ORDER BY c.nombre
        """), {"uid": actor.id}).mappings().all()
        return {"companias": [dict(r) for r in rows]}

@app.get("/v1/companies/{company_id}/permissions")
def grid(company_id: int = Path(gt=0), actor: Actor = Depends(get_actor)):
    with engine.begin() as connection:
        company = support_company(connection, actor, company_id)
        ids = connection.execute(text("""
            SELECT u.id FROM usuarios_plataforma u
            JOIN usuario_companias_plataforma uc ON uc.usuario_id = u.id
            WHERE uc.compania_id = :cid AND u.activo = TRUE ORDER BY u.id
        """), {"cid": company_id}).scalars().all()
        users = []
        for uid in ids:
            # Exclude administrators and invalid/ambiguous role or tenant assignments.
            roles = set(connection.execute(text("""
                SELECT r.nombre FROM roles_plataforma r
                JOIN usuario_roles_plataforma ur ON ur.rol_id = r.id
                WHERE ur.usuario_id = :uid AND r.activo = TRUE
            """), {"uid": uid}).scalars())
            if len(roles) != 1 or not roles.issubset(LEADER_ROLES):
                continue
            count = connection.execute(text("""
                SELECT COUNT(*) FROM usuario_companias_plataforma uc
                JOIN companias c ON c.id = uc.compania_id
                WHERE uc.usuario_id = :uid AND c.activo = TRUE
            """), {"uid": uid}).scalar_one()
            if count != 1:
                continue
            user, role, cid = leader(connection, uid, company_id)
            users.append({**user, "rol": role, "permisos": grants(connection, uid, cid, role)})
        return {"compania": company, "usuarios": users}

@app.put("/v1/companies/{company_id}/users/{user_id}/permissions/{code}")
def change_permission(
    change: Change, code: str, company_id: int = Path(gt=0),
    user_id: int = Path(gt=0), actor: Actor = Depends(get_actor),
):
    with engine.begin() as connection:
        support_company(connection, actor, company_id)
        _, role, _ = leader(connection, user_id, company_id)
        item = PERMISSIONS.get(code)
        if item is None or item["rol"] != role:
            raise HTTPException(403, "Permiso incompatible con el rol del usuario")
        params = {"uid": user_id, "cid": company_id, "code": code}
        previous = connection.execute(text("""
            SELECT habilitado, version FROM permisos_usuario_compania
            WHERE usuario_id = :uid AND compania_id = :cid AND codigo = :code FOR UPDATE
        """), params).mappings().first()
        version = previous["version"] if previous else 0
        if change.version != version:
            raise HTTPException(409, "El permiso cambió; actualice la grilla")
        if previous is not None and previous["habilitado"] == change.habilitado:
            return {"codigo": code, "habilitado": change.habilitado, "version": version}
        updated = connection.execute(text("""
            INSERT INTO permisos_usuario_compania (
                usuario_id, compania_id, codigo, habilitado, version, modificado_por
            ) VALUES (:uid, :cid, :code, :enabled, 1, :actor)
            ON CONFLICT (usuario_id, compania_id, codigo) DO UPDATE SET
                habilitado = EXCLUDED.habilitado,
                version = permisos_usuario_compania.version + 1,
                modificado_por = EXCLUDED.modificado_por, fecha_modificacion = NOW()
            RETURNING version
        """), {**params, "enabled": change.habilitado, "actor": actor.id}).scalar_one()
        connection.execute(text("""
            INSERT INTO auditoria_outbox (
                evento_uuid, fecha_evento, servicio, evento, resultado,
                actor_usuario_id, objetivo_usuario_id, compania_id, detalle
            ) VALUES (
                CAST(:event AS UUID), NOW(), 'permissions-service',
                'PERMISO_USUARIO_MODIFICADO', 'EXITO', :actor, :uid, :cid,
                CAST(:detail AS JSONB)
            )
        """), {
            **params, "actor": actor.id, "event": str(uuid4()),
            "detail": json.dumps({
                "permiso": code, "habilitado_anterior": bool(previous["habilitado"]) if previous else False,
                "habilitado_nuevo": change.habilitado, "version": updated,
            }),
        })
        return {"codigo": code, "habilitado": change.habilitado, "version": updated}

def own_grants(connection, actor):
    _, role, cid = leader(connection, actor.id)
    return cid, grants(connection, actor.id, cid, role)

@app.get("/v1/me/permissions")
def mine(actor: Actor = Depends(get_actor)):
    with engine.begin() as connection:
        cid, items = own_grants(connection, actor)
        return {"compania_id": cid, "permisos": items}

@app.get("/v1/me/views/{code}")
def reference_view(code: str, actor: Actor = Depends(get_actor)):
    with engine.begin() as connection:
        cid, items = own_grants(connection, actor)
        item = next((i for i in items if i["codigo"] == code and i["habilitado"]), None)
        if item is None:
            raise HTTPException(403, "Permiso no habilitado")
        return {"compania_id": cid, "titulo": item["titulo"],
                "descripcion": item["descripcion"], "tipo": "VISTA_DE_REFERENCIA"}
