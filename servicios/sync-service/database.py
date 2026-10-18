import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# IAM SECURE - SYNC WORKER
# CONEXIÓN SEGURA A POSTGRESQL
# ============================================================
#
# El worker obtiene toda la configuración desde variables de
# entorno. Ninguna contraseña o cadena de conexión debe quedar
# hardcodeada en el código fuente o en el repositorio.
# ============================================================

load_dotenv()


def _obtener_variable_requerida(nombre: str) -> str:
    """
    Obtiene una variable de entorno obligatoria.

    SEGURIDAD:
    - no imprime el valor;
    - no registra secretos;
    - el error indica únicamente el nombre de la variable.
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


# ============================================================
# VALIDACIÓN DEL PUERTO
# ============================================================

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


# ============================================================
# URL DE CONEXIÓN
# ============================================================
#
# URL.create() evita construir manualmente una cadena que pueda
# manejar incorrectamente caracteres especiales de la contraseña.
# ============================================================

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT_INT,
    database=DB_NAME,
)


# ============================================================
# MOTOR SQLALCHEMY
# ============================================================
#
# pool_pre_ping=True permite comprobar una conexión reutilizada
# antes de entregarla al worker.
#
# No usamos echo=True porque los SQL y sus parámetros no deben
# aparecer innecesariamente en los logs.
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def verificar_conexion() -> None:
    """
    Comprueba que PostgreSQL esté disponible.

    No devuelve ni registra parámetros de conexión.
    """
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))
