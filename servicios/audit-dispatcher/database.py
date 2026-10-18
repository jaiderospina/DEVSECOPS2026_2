import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# IAM SECURE - AUDIT DISPATCHER
# CONEXION SEGURA A POSTGRESQL
# ============================================================

load_dotenv()


def _variable_requerida(nombre: str) -> str:
    valor = os.getenv(nombre)

    if valor is None or not valor.strip():
        raise RuntimeError(
            f"Falta la variable de entorno requerida: {nombre}"
        )

    return valor.strip()


DB_USER = _variable_requerida("DB_USER")
DB_PASSWORD = _variable_requerida("DB_PASSWORD")
DB_HOST = _variable_requerida("DB_HOST")
DB_PORT = _variable_requerida("DB_PORT")
DB_NAME = _variable_requerida("DB_NAME")


try:
    DB_PORT_INT = int(DB_PORT)
except ValueError as exc:
    raise RuntimeError(
        "DB_PORT debe ser un numero entero"
    ) from exc


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
    with engine.connect() as conexion:
        conexion.execute(
            text("SELECT 1")
        )
