from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine


app = FastAPI(
    title="Microservicio de Usuarios de Plataforma",
    version="1.0.0"
)


class UsuarioCrear(BaseModel):
    nombre: str
    email: EmailStr


class UsuarioModificar(BaseModel):
    nombre: str
    email: EmailStr


class UsuarioEstado(BaseModel):
    activo: bool


@app.get("/")
def inicio():
    return {
        "servicio": "usuarios_plataforma",
        "estado": "funcionando"
    }


@app.post("/usuarios", status_code=201)
def crear_usuario(datos: UsuarioCrear):
    consulta = text("""
        INSERT INTO usuarios_plataforma (
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (
            :nombre,
            :email,
            TRUE,
            NOW(),
            NOW()
        )
        RETURNING
            id,
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    try:
        with engine.begin() as conexion:
            resultado = conexion.execute(
                consulta,
                {
                    "nombre": datos.nombre,
                    "email": datos.email
                }
            )

            usuario = resultado.mappings().one()

        return dict(usuario)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="El correo electrónico ya está registrado"
        )


@app.get("/usuarios")
def obtener_usuarios():
    consulta = text("""
        SELECT
            id,
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
        FROM usuarios_plataforma
        ORDER BY id
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(consulta)

        usuarios = [
            dict(usuario)
            for usuario in resultado.mappings().all()
        ]

    return {
        "total": len(usuarios),
        "usuarios": usuarios
    }


@app.get("/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: int):
    consulta = text("""
        SELECT
            id,
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
        FROM usuarios_plataforma
        WHERE id = :usuario_id
    """)

    with engine.connect() as conexion:
        resultado = conexion.execute(
            consulta,
            {"usuario_id": usuario_id}
        )

        usuario = resultado.mappings().first()

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return dict(usuario)


@app.put("/usuarios/{usuario_id}")
def modificar_usuario(
    usuario_id: int,
    datos: UsuarioModificar
):
    consulta = text("""
        UPDATE usuarios_plataforma
        SET
            nombre = :nombre,
            email = :email,
            fecha_modificacion = NOW()
        WHERE id = :usuario_id
        RETURNING
            id,
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    try:
        with engine.begin() as conexion:
            resultado = conexion.execute(
                consulta,
                {
                    "usuario_id": usuario_id,
                    "nombre": datos.nombre,
                    "email": datos.email
                }
            )

            usuario = resultado.mappings().first()

        if usuario is None:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        return dict(usuario)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="El correo electrónico ya está registrado"
        )


@app.patch("/usuarios/{usuario_id}/estado")
def cambiar_estado_usuario(
    usuario_id: int,
    datos: UsuarioEstado
):
    consulta = text("""
        UPDATE usuarios_plataforma
        SET
            activo = :activo,
            fecha_modificacion = NOW()
        WHERE id = :usuario_id
        RETURNING
            id,
            nombre,
            email,
            activo,
            fecha_creacion,
            fecha_modificacion
    """)

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "usuario_id": usuario_id,
                "activo": datos.activo
            }
        )

        usuario = resultado.mappings().first()

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return dict(usuario)