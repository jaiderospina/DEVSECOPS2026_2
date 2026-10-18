import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# IAM SECURE - AUDIT SERVICE
# CONEXIÓN SEGURA A POSTGRESQL
# ============================================================
#
# Ninguna credencial queda hardcodeada en el microservicio.
# Toda la configuración se obtiene desde variables de entorno.
# ============================================================

load_dotenv()


def _obtener_variable_requerida(nombre: str) -> str:
    """
    Obtiene una variable obligatoria sin registrar su contenido.
    """
    valor = os.getenv(nombre)

    if valor is None or not valor.strip():
        raise RuntimeError(
            f"Falta la variable de entorno requerida: {nombre}"
        )

    return valor.strip()


DB_USER = _obtener_variable_requerida("DB_USER")
DB_PASSWORD = _obtener_variable_requerida("DB_PASSWORD")
DB_HOST = _obtener_variable_requerida("DB_HOST")
DB_PORT = _obtener_variable_requerida("DB_PORT")
DB_NAME = _obtener_variable_requerida("DB_NAME")


try:
    DB_PORT_INT = int(DB_PORT)
except ValueError as exc:
    raise RuntimeError(
        "DB_PORT debe ser un número entero válido"
    ) from exc

if not 1 <= DB_PORT_INT <= 65535:
    raise RuntimeError(
        "DB_PORT debe estar entre 1 y 65535"
    )


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT_INT,
    database=DB_NAME,
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def verificar_conexion() -> None:
    """
    Comprueba disponibilidad de PostgreSQL sin exponer datos
    de conexión.
    """
    with engine.connect() as conexion:
        conexion.execute(
            text("SELECT 1")
        )
