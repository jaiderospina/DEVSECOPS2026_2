    # --------------------------------------------------------

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()

def _obtener_variable_requerida(nombre: str) -> str:
    """
    Obtiene una variable de entorno obligatoria.

    SEGURIDAD:
    - no imprime ni registra el valor;
    - no incluye el secreto en el mensaje de error;
    - elimina únicamente espacios accidentales externos.
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
# VALIDAR PUERTO
# ============================================================
# Se valida antes de construir la URL para producir un error de
# configuración controlado sin exponer la cadena de conexión.
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
# URL.create() evita concatenar manualmente usuario/contraseña
# y maneja correctamente caracteres especiales del secreto.
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
# pool_pre_ping comprueba que una conexión reutilizada continúe
# disponible antes de entregarla a la aplicación. Esto mejora la
# recuperación ante reinicios breves de PostgreSQL/Docker.
#
# No se habilita echo=True porque podría registrar sentencias SQL
# y parámetros que no deben aparecer innecesariamente en logs.
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# --------------------------------------------------------
