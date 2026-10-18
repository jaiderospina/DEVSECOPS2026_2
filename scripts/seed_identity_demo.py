import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pwdlib import PasswordHash
from sqlalchemy import URL, create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_HOST_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "iam_secure")

DEMO_PASSWORD = os.getenv("DEMO_IDENTITY_PASSWORD")


if not DB_PASSWORD:
    print(
        "ERROR: No se encontró POSTGRES_PASSWORD "
        "en el archivo .env"
    )
    sys.exit(1)


if not DEMO_PASSWORD:
    print(
        "ERROR: No se encontró DEMO_IDENTITY_PASSWORD "
        "en el archivo .env"
    )
    sys.exit(1)


if len(DEMO_PASSWORD) < 12:
    print(
        "ERROR: DEMO_IDENTITY_PASSWORD debe tener "
        "como mínimo 12 caracteres."
    )
    sys.exit(1)


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_engine(DATABASE_URL)

password_hasher = PasswordHash.recommended()


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

COMPANIAS = [
    {
        "codigo": "ANDINA",
        "nombre": "Andina Tecnología S.A.S.",
        "descripcion": "Compañía ficticia para demostración IAM/IGA",
    },
    {
        "codigo": "CARIBE",
        "nombre": "Caribe Logística S.A.S.",
        "descripcion": "Compañía ficticia para demostración IAM/IGA",
    },
    {
        "codigo": "PACIFICO",
        "nombre": "Pacífico Financiero S.A.S.",
        "descripcion": "Compañía ficticia para demostración IAM/IGA",
    },
]


USUARIOS = [
    {
        "nombre": "Ana Torres",
        "email": "ana.torres@andina.demo",
        "rol": "ADMIN",
        "compania": "ANDINA",
    },
    {
        "nombre": "Carlos Mendoza",
        "email": "carlos.mendoza@andina.demo",
        "rol": "ANALYST",
        "compania": "ANDINA",
    },
    {
        "nombre": "Laura Gómez",
        "email": "laura.gomez@andina.demo",
        "rol": "VIEWER",
        "compania": "ANDINA",
    },

    {
        "nombre": "Andrés Ruiz",
        "email": "andres.ruiz@caribe.demo",
        "rol": "ADMIN",
        "compania": "CARIBE",
    },
    {
        "nombre": "Diana Martínez",
        "email": "diana.martinez@caribe.demo",
        "rol": "ANALYST",
        "compania": "CARIBE",
    },
    {
        "nombre": "Felipe Castro",
        "email": "felipe.castro@caribe.demo",
        "rol": "VIEWER",
        "compania": "CARIBE",
    },

    {
        "nombre": "Marcela Rojas",
        "email": "marcela.rojas@pacifico.demo",
        "rol": "ADMIN",
        "compania": "PACIFICO",
    },
    {
        "nombre": "Juan Herrera",
        "email": "juan.herrera@pacifico.demo",
        "rol": "ANALYST",
        "compania": "PACIFICO",
    },
    {
        "nombre": "Natalia Vargas",
        "email": "natalia.vargas@pacifico.demo",
        "rol": "VIEWER",
        "compania": "PACIFICO",
    },
]


# ============================================================
# FUNCIONES
# ============================================================

def obtener_o_crear_compania(conexion, datos):
    compania = conexion.execute(
        text("""
            SELECT id
            FROM companias
            WHERE codigo = :codigo
        """),
        {
            "codigo": datos["codigo"]
        },
    ).mappings().first()

    if compania:
        print(
            f"[EXISTE] Compañía {datos['codigo']}"
        )
        return compania["id"]

    compania_id = conexion.execute(
        text("""
            INSERT INTO companias (
                codigo,
                nombre,
                descripcion,
                activo,
                fecha_creacion,
                fecha_modificacion
            )
            VALUES (
                :codigo,
                :nombre,
                :descripcion,
                TRUE,
                NOW(),
                NOW()
            )
            RETURNING id
        """),
        datos,
    ).scalar_one()

    print(
        f"[CREADA] Compañía {datos['codigo']}"
    )

    return compania_id


def obtener_o_crear_usuario(conexion, datos):
    usuario = conexion.execute(
        text("""
            SELECT id
            FROM usuarios_plataforma
            WHERE email = :email
        """),
        {
            "email": datos["email"]
        },
    ).mappings().first()

    if usuario:
        print(
            f"[EXISTE] Usuario {datos['email']}"
        )
        return usuario["id"]

    usuario_id = conexion.execute(
        text("""
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
            RETURNING id
        """),
        {
            "nombre": datos["nombre"],
            "email": datos["email"],
        },
    ).scalar_one()

    print(
        f"[CREADO] Usuario {datos['email']}"
    )

    return usuario_id


def asegurar_credencial(conexion, usuario_id):
    credencial = conexion.execute(
        text("""
            SELECT id
            FROM credenciales
            WHERE usuario_id = :usuario_id
        """),
        {
            "usuario_id": usuario_id
        },
    ).first()

    if credencial:
        return

    password_hash = password_hasher.hash(
        DEMO_PASSWORD
    )

    conexion.execute(
        text("""
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
        """),
        {
            "usuario_id": usuario_id,
            "password_hash": password_hash,
        },
    )


def asegurar_rol(conexion, usuario_id, rol):
    rol_id = conexion.execute(
        text("""
            SELECT id
            FROM roles_plataforma
            WHERE nombre = :rol
              AND activo = TRUE
        """),
        {
            "rol": rol
        },
    ).scalar_one_or_none()

    if rol_id is None:
        raise RuntimeError(
            f"No existe el rol activo {rol}"
        )

    conexion.execute(
        text("""
            INSERT INTO usuario_roles_plataforma (
                usuario_id,
                rol_id,
                fecha_asignacion
            )
            VALUES (
                :usuario_id,
                :rol_id,
                NOW()
            )
            ON CONFLICT (
                usuario_id,
                rol_id
            )
            DO NOTHING
        """),
        {
            "usuario_id": usuario_id,
            "rol_id": rol_id,
        },
    )


def asegurar_compania(
    conexion,
    usuario_id,
    compania_id,
):
    conexion.execute(
        text("""
            INSERT INTO usuario_companias_plataforma (
                usuario_id,
                compania_id,
                fecha_asignacion
            )
            VALUES (
                :usuario_id,
                :compania_id,
                NOW()
            )
            ON CONFLICT (
                usuario_id,
                compania_id
            )
            DO NOTHING
        """),
        {
            "usuario_id": usuario_id,
            "compania_id": compania_id,
        },
    )


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():
    print("")
    print("========================================")
    print(" IAM Secure - Dataset de demostración")
    print("========================================")
    print("")

    companias_ids = {}

    with engine.begin() as conexion:

        for compania in COMPANIAS:
            compania_id = obtener_o_crear_compania(
                conexion,
                compania,
            )

            companias_ids[
                compania["codigo"]
            ] = compania_id

        for usuario in USUARIOS:
            usuario_id = obtener_o_crear_usuario(
                conexion,
                usuario,
            )

            asegurar_credencial(
                conexion,
                usuario_id,
            )

            asegurar_rol(
                conexion,
                usuario_id,
                usuario["rol"],
            )

            asegurar_compania(
                conexion,
                usuario_id,
                companias_ids[
                    usuario["compania"]
                ],
            )

    print("")
    print("Dataset creado correctamente.")
    print("")
    print("Compañías demo: 3")
    print("Usuarios demo: 9")
    print("")


if __name__ == "__main__":
    main()