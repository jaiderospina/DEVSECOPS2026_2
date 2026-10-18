"""Configuración DB compartida; nunca imprimir la URL ni sus credenciales."""
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("Falta configuración de base de datos")
    return value

url = URL.create(
    "postgresql+psycopg2",
    username=required("DB_USER"), password=required("DB_PASSWORD"),
    host=required("DB_HOST"), port=int(required("DB_PORT")),
    database=required("DB_NAME"),
)
engine = create_engine(url, pool_pre_ping=True, echo=False)
