from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Response
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "servicios" / "audit-service"


# ============================================================
# CONFIGURACIÓN FICTICIA DE PRUEBAS
# ============================================================
# Ningún valor corresponde a credenciales reales.
# Las pruebas no realizan conexiones de red ni a PostgreSQL.
# ============================================================

os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password_not_real"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_db"

os.environ["AUDIT_INTERNAL_TOKEN"] = "A" * 64


if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


def _cargar_modulo(nombre: str, ruta: Path):
    spec = importlib.util.spec_from_file_location(
        nombre,
        ruta,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"No fue posible cargar módulo: {nombre}"
        )

    modulo = importlib.util.module_from_spec(spec)

    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)

    return modulo


# Evita colisiones con módulos homónimos de otros servicios.
sys.modules.pop("database", None)
sys.modules.pop("seguridad", None)

database = _cargar_modulo(
    "database",
    SERVICE_DIR / "database.py",
)

seguridad = _cargar_modulo(
    "seguridad",
    SERVICE_DIR / "seguridad.py",
)

audit_main = _cargar_modulo(
    "iam_audit_service_main",
    SERVICE_DIR / "main.py",
)


# ============================================================
# DOBLES DE PRUEBA SQLALCHEMY
# ============================================================

class FakeMappings:

    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class FakeResult:

    def __init__(
        self,
        row=None,
        rowcount=0,
    ):
        self._row = row
        self.rowcount = rowcount

    def mappings(self):
        return FakeMappings(
            self._row
        )


class FakeConnection:

    def __init__(
        self,
        results=None,
        error=None,
    ):
        self._results = list(
            results or []
        )

        self._error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def execute(
        self,
        statement,
        params=None,
    ):
        self.calls.append(
            {
                "sql": str(statement),
                "params": params or {},
            }
        )

        if self._error is not None:
            raise self._error

        if not self._results:
            raise AssertionError(
                "Se ejecutaron más consultas SQL "
                "de las esperadas"
            )

        return self._results.pop(0)


class FakeEngine:

    def __init__(
        self,
        results=None,
        error=None,
    ):
        self.connection = FakeConnection(
            results=results,
            error=error,
        )

    def begin(self):
        return self.connection


# ============================================================
# EVENTO BASE
# ============================================================

def _evento_base() -> dict:
    return {
        "evento_uuid": uuid4(),

        "fecha_evento":
            datetime.now(
                timezone.utc
            ),

        "servicio":
            "identity-service",

        "evento":
            "PRUEBA_AUTOMATIZADA",

        "resultado":
            "EXITO",

        "actor_usuario_id":
            18,

        "objetivo_usuario_id":
            34,

        "compania_id":
            6,

        "detalle": {
            "origen":
                "unittest"
        },
    }


# ============================================================
# SANITIZACIÓN
# ============================================================

class TestSanitizacion(unittest.TestCase):

    def test_redacta_campos_sensibles_anidados(self):
        resultado = seguridad.sanitizar_detalle(
            {
                "password":
                    "VALOR_FICTICIO",

                "access_token":
                    "TOKEN_FICTICIO",

                "datos": {
                    "totp_secret":
                        "SECRETO_FICTICIO",

                    "campo_seguro":
                        "visible",
                },
            }
        )

        self.assertEqual(
            resultado["password"],
            "[REDACTED]",
        )

        self.assertEqual(
            resultado["access_token"],
            "[REDACTED]",
        )

        self.assertEqual(
            resultado[
                "datos"
            ][
                "totp_secret"
            ],
            "[REDACTED]",
        )

        self.assertEqual(
            resultado[
                "datos"
            ][
                "campo_seguro"
            ],
            "visible",
        )

    def test_objeto_desconocido_no_expone_str(self):

        class ObjetoPeligroso:

            def __str__(self):
                return (
                    "PASSWORD_FICTICIO_NO_DEBE_SALIR"
                )

        resultado = seguridad.sanitizar_detalle(
            {
                "objeto":
                    ObjetoPeligroso()
            }
        )

        self.assertEqual(
            resultado["objeto"],
            "[UNSUPPORTED_TYPE]",
        )


# ============================================================
# MODELO PYDANTIC
# ============================================================

class TestModeloEvento(unittest.TestCase):

    def test_rechaza_campos_extra(self):
        datos = _evento_base()

        datos["campo_no_permitido"] = (
            "valor"
        )

        with self.assertRaises(
            ValidationError
        ):
            audit_main.EventoAuditoriaEntrada(
                **datos
            )

    def test_rechaza_fecha_sin_zona_horaria(self):
        datos = _evento_base()

        datos["fecha_evento"] = (
            datetime.now()
        )

        with self.assertRaises(
            ValidationError
        ):
            audit_main.EventoAuditoriaEntrada(
                **datos
            )


# ============================================================
# AUTENTICACIÓN INTERNA
# ============================================================

class TestAutenticacionInterna(unittest.TestCase):

    def test_acepta_token_correcto(self):
        audit_main.validar_token_interno(
            "A" * 64
        )

    def test_rechaza_token_ausente(self):
        with self.assertRaises(
            HTTPException
        ) as contexto:
            audit_main.validar_token_interno(
                None
            )

        self.assertEqual(
            contexto.exception.status_code,
            401,
        )

    def test_rechaza_token_incorrecto(self):
        with self.assertRaises(
            HTTPException
        ) as contexto:
            audit_main.validar_token_interno(
                "B" * 64
            )

        self.assertEqual(
            contexto.exception.status_code,
            401,
        )


# ============================================================
# PERSISTENCIA E IDEMPOTENCIA
# ============================================================

class TestCrearEvento(unittest.TestCase):

    def test_crea_evento_y_sanitiza_detalle(self):
        datos = _evento_base()

        datos["detalle"] = {
            "password":
                "VALOR_FICTICIO",

            "campo_seguro":
                "visible",
        }

        evento = (
            audit_main.EventoAuditoriaEntrada(
                **datos
            )
        )

        fake_engine = FakeEngine(
            [
                FakeResult(
                    row={
                        "id": 101
                    }
                )
            ]
        )

        respuesta_http = Response()

        with patch.object(
            audit_main,
            "engine",
            fake_engine,
        ):
            respuesta = (
                audit_main.crear_evento(
                    evento,
                    respuesta_http,
                    None,
                )
            )

        self.assertEqual(
            respuesta.id,
            101,
        )

        self.assertTrue(
            respuesta.creado
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "ON CONFLICT (evento_uuid)",
            llamada["sql"],
        )

        detalle_guardado = json.loads(
            llamada[
                "params"
            ][
                "detalle"
            ]
        )

        self.assertEqual(
            detalle_guardado[
                "password"
            ],
            "[REDACTED]",
        )

        self.assertEqual(
            detalle_guardado[
                "campo_seguro"
            ],
            "visible",
        )

    def test_reintento_idempotente_no_duplica(self):
        datos = _evento_base()

        evento = (
            audit_main.EventoAuditoriaEntrada(
                **datos
            )
        )

        fake_engine = FakeEngine(
            [
                FakeResult(
                    row=None
                ),

                FakeResult(
                    row={
                        "id": 202
                    }
                ),
            ]
        )

        respuesta_http = Response()

        with patch.object(
            audit_main,
            "engine",
            fake_engine,
        ):
            respuesta = (
                audit_main.crear_evento(
                    evento,
                    respuesta_http,
                    None,
                )
            )

        self.assertEqual(
            respuesta.id,
            202,
        )

        self.assertFalse(
            respuesta.creado
        )

        self.assertEqual(
            respuesta_http.status_code,
            200,
        )

        self.assertEqual(
            len(
                fake_engine
                .connection
                .calls
            ),
            2,
        )

    def test_rechaza_detalle_excesivamente_grande(self):
        datos = _evento_base()

        datos["detalle"] = {
            "campo_seguro":
                "X" * 20000
        }

        evento = (
            audit_main.EventoAuditoriaEntrada(
                **datos
            )
        )

        with self.assertRaises(
            HTTPException
        ) as contexto:
            audit_main.crear_evento(
                evento,
                Response(),
                None,
            )

        self.assertEqual(
            contexto.exception.status_code,
            413,
        )

    def test_error_db_no_expone_mensaje_bruto(self):
        datos = _evento_base()

        evento = (
            audit_main.EventoAuditoriaEntrada(
                **datos
            )
        )

        mensaje_sensible = (
            "PASSWORD=VALOR_FICTICIO_NO_REAL"
        )

        fake_engine = FakeEngine(
            error=RuntimeError(
                mensaje_sensible
            )
        )

        with (
            patch.object(
                audit_main,
                "engine",
                fake_engine,
            ),
            patch.object(
                audit_main.logger,
                "error",
            ) as log_error,
        ):
            with self.assertRaises(
                HTTPException
            ) as contexto:
                audit_main.crear_evento(
                    evento,
                    Response(),
                    None,
                )

        self.assertEqual(
            contexto.exception.status_code,
            500,
        )

        self.assertNotIn(
            mensaje_sensible,
            str(
                log_error.call_args
            ),
        )


# ============================================================
# HEALTHCHECK
# ============================================================

class TestHealth(unittest.TestCase):

    def test_health_correcto(self):
        with patch.object(
            audit_main,
            "verificar_conexion",
        ):
            respuesta = (
                audit_main.health()
            )

        self.assertEqual(
            respuesta,
            {
                "status": "ok"
            },
        )

    def test_health_db_caida_retorna_503(self):
        with patch.object(
            audit_main,
            "verificar_conexion",
            side_effect=RuntimeError(
                "DB test unavailable"
            ),
        ):
            with self.assertRaises(
                HTTPException
            ) as contexto:
                audit_main.health()

        self.assertEqual(
            contexto.exception.status_code,
            503,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
