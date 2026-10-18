import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine


load_dotenv()


app = FastAPI(
    title="Microservicio de Autenticación",
    version="1.0.0"
)


password_hasher = PasswordHash.recommended()

bearer_scheme = HTTPBearer()


JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRE_MINUTES", "30")
)

if not JWT_SECRET:
    raise RuntimeError(
        "La variable JWT_SECRET no está configurada"
    )


class CredencialCrear(BaseModel):
    usuario_id: int
    password: str = Field(min_length=12)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.get("/")
def inicio():
    return {
        "servicio": "autenticacion",
        "estado": "funcionando"
    }


@app.post("/auth/credenciales", status_code=201)
def registrar_credencial(datos: CredencialCrear):

    consulta_usuario = text("""
        SELECT id
        FROM usuarios_plataforma
        WHERE id = :usuario_id
    """)

    with engine.connect() as conexion:
        usuario = conexion.execute(
            consulta_usuario,
            {"usuario_id": datos.usuario_id}
        ).first()

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    hash_generado = password_hasher.hash(
        datos.password
    )

    consulta = text("""
        INSERT INTO credenciales (
            usuario_id,
            password_hash,
            activo,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (
            :usuario_id,
            :password_hash,
            TRUE,
            NOW(),
            NOW()
        )
        RETURNING
            id,
            usuario_id,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    try:
        with engine.begin() as conexion:
            resultado = conexion.execute(
                consulta,
                {
                    "usuario_id": datos.usuario_id,
                    "password_hash": hash_generado
                }
            )

            credencial = resultado.mappings().one()

        return dict(credencial)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=(
                "El usuario ya tiene una "
                "credencial registrada"
            )
        )


@app.post("/auth/login")
def login(datos: LoginRequest):

    consulta = text("""
        SELECT
            u.id AS usuario_id,
            u.email,
            u.activo AS usuario_activo,
            c.password_hash,
            c.activo AS credencial_activa
        FROM usuarios_plataforma u
        JOIN credenciales c
            ON c.usuario_id = u.id
        WHERE u.email = :email
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(
            consulta,
            {"email": datos.email}
        )

        registro = resultado.mappings().first()

    if registro is None:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    if not registro["usuario_activo"]:
        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo"
        )

    if not registro["credencial_activa"]:
        raise HTTPException(
            status_code=403,
            detail="Credencial inactiva"
        )

    password_valida = password_hasher.verify(
        datos.password,
        registro["password_hash"]
    )

    if not password_valida:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    consulta_roles = text("""
        SELECT r.nombre
        FROM roles_plataforma r
        JOIN usuario_roles_plataforma ur
            ON ur.rol_id = r.id
        WHERE ur.usuario_id = :usuario_id
          AND r.activo = TRUE
        ORDER BY r.nombre
    """)

    with engine.connect() as conexion:
        resultado_roles = conexion.execute(
            consulta_roles,
            {"usuario_id": registro["usuario_id"]}
        )

        roles = [
            fila[0]
            for fila in resultado_roles.fetchall()
        ]

    ahora = datetime.now(timezone.utc)

    expira = ahora + timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(registro["usuario_id"]),
        "email": registro["email"],
        "roles": roles,
        "iat": ahora,
        "exp": expira
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60
    }


def obtener_usuario_desde_token(
    credenciales: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
):
    token = credenciales.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expirado"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    usuario_id = payload.get("sub")
    roles = payload.get("roles", [])

    if usuario_id is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    consulta = text("""
        SELECT
            id,
            nombre,
            email,
            activo
        FROM usuarios_plataforma
        WHERE id = :usuario_id
    """)

    with engine.connect() as conexion:
        usuario = conexion.execute(
            consulta,
            {"usuario_id": int(usuario_id)}
        ).mappings().first()

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )

    if not usuario["activo"]:
        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo"
        )

    usuario_autenticado = dict(usuario)
    usuario_autenticado["roles"] = roles

    return usuario_autenticado


@app.get("/auth/me")
def obtener_mi_usuario(
    usuario=Depends(obtener_usuario_desde_token)
):
    return usuario