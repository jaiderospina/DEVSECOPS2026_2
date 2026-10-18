from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "servicios" / "audit-dispatcher"


# ============================================================
# CONFIGURACIÓN FICTICIA DE PRUEBAS
# ============================================================
# Ningún valor corresponde a credenciales reales.
# No se realizan conexiones reales a PostgreSQL ni HTTP.
# ============================================================

os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password_not_real"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_db"

os.environ["AUDIT_SERVICE_URL"] = "http://audit-service-test:8004"
os.environ["AUDIT_INTERNAL_TOKEN"] = "A" * 64
os.environ["AUDIT_HTTP_TIMEOUT_SECONDS"] = "2"

os.environ["AUDIT_DISPATCH_POLL_SECONDS"] = "1"
os.environ["AUDIT_DISPATCH_RETRY_DELAY_SECONDS"] = "5"
os.environ["AUDIT_DISPATCH_MAX_ATTEMPTS"] = "5"
os.environ["AUDIT_DISPATCH_JOB_TIMEOUT_SECONDS"] = "30"
os.environ["AUDIT_DISPATCH_RECOVERY_CHECK_SECONDS"] = "10"
os.environ["AUDIT_DISPATCH_WORKER_ID"] = "audit-test-worker"


if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SERVICE_DIR),
    )


def _cargar_modulo(
    nombre: str,
    ruta: Path,
):
    spec = importlib.util.spec_from_file_location(
        nombre,
        ruta,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"No fue posible cargar módulo: {nombre}"
        )

    modulo = importlib.util.module_from_spec(
        spec
    )

    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)

    return modulo


# ============================================================
# CARGA CONTROLADA DE MÓDULOS
# ============================================================

sys.modules.pop("database", None)
sys.modules.pop("audit_client", None)

database = _cargar_modulo(
    "database",
    SERVICE_DIR / "database.py",
)

audit_client = _cargar_modulo(
    "audit_client",
    SERVICE_DIR / "audit_client.py",
)

worker = _cargar_modulo(
    "iam_audit_dispatcher_main",
    SERVICE_DIR / "main.py",
)


class TestTerminalFailureAlert(unittest.TestCase):
    def test_terminal_failure_alert_has_no_event_payload(self):
        job = _trabajo_base()
        job["intentos"] = worker.MAX_ATTEMPTS
        with patch.object(worker, "enviar_evento", return_value=(False, "NO_DISPONIBLE")), \
                patch.object(worker, "marcar_error", return_value=True), \
                patch.object(worker.logger, "error") as alert:
            worker.procesar(job)
        alert.assert_called_once_with("AUDIT_OUTBOX_FALLIDO id=%s intentos=%s", job["id"], worker.MAX_ATTEMPTS)

    def test_retry_does_not_report_terminal_failure(self):
        job = _trabajo_base()
        job["intentos"] = worker.MAX_ATTEMPTS - 1
        with patch.object(worker, "enviar_evento", return_value=(False, "NO_DISPONIBLE")), \
                patch.object(worker, "marcar_error", return_value=True), \
                patch.object(worker.logger, "error") as alert:
            worker.procesar(job)
        alert.assert_not_called()

    def test_lost_worker_ownership_does_not_report_written_failure(self):
        job = _trabajo_base()
        job["intentos"] = worker.MAX_ATTEMPTS
        with patch.object(worker, "enviar_evento", return_value=(False, "NO_DISPONIBLE")), \
                patch.object(worker, "marcar_error", return_value=False), \
                patch.object(worker.logger, "error") as alert:
            worker.procesar(job)
        alert.assert_not_called()


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

    def __init__(self, results):
        self._results = list(results)
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

        if not self._results:
            raise AssertionError(
                "Se ejecutaron más consultas SQL "
                "de las esperadas"
            )

        return self._results.pop(0)


class FakeEngine:

    def __init__(self, results):
        self.connection = FakeConnection(
            results
        )

    def begin(self):
        return self.connection


# ============================================================
# RESPUESTA HTTP SIMULADA
# ============================================================

class FakeHTTPResponse:

    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


# ============================================================
# TRABAJO BASE
# ============================================================

def _trabajo_base(
    *,
    intentos=1,
):
    return {
        "id": 101,

        "evento_uuid":
            "11111111-1111-4111-8111-111111111111",

        "fecha_evento":
            datetime.now(
                timezone.utc
            ),

        "servicio":
            "identity-service",

        "evento":
            "LOGIN_FALLIDO",

        "resultado":
            "FALLO",

        "actor_usuario_id":
            None,

        "objetivo_usuario_id":
            None,

        "compania_id":
            None,

        "detalle": {
            "motivo":
                "CREDENCIALES_INVALIDAS"
        },

        "intentos":
            intentos,
    }


# ============================================================
# CONFIGURACIÓN
# ============================================================

class TestConfiguracionDispatcher(unittest.TestCase):

    def test_entero_positivo_acepta_valor(self):
        with patch.dict(
            os.environ,
            {
                "AUDIT_TEST_INTEGER":
                    "7"
            },
            clear=False,
        ):
            resultado = worker._entero_positivo(
                "AUDIT_TEST_INTEGER",
                5,
            )

        self.assertEqual(
            resultado,
            7,
        )

    def test_entero_positivo_rechaza_texto(self):
        with patch.dict(
            os.environ,
            {
                "AUDIT_TEST_INTEGER":
                    "abc"
            },
            clear=False,
        ):
            with self.assertRaises(
                RuntimeError
            ):
                worker._entero_positivo(
                    "AUDIT_TEST_INTEGER",
                    5,
                )

    def test_entero_positivo_rechaza_cero(self):
        with patch.dict(
            os.environ,
            {
                "AUDIT_TEST_INTEGER":
                    "0"
            },
            clear=False,
        ):
            with self.assertRaises(
                RuntimeError
            ):
                worker._entero_positivo(
                    "AUDIT_TEST_INTEGER",
                    5,
                )


# ============================================================
# CLAIM / FOR UPDATE SKIP LOCKED
# ============================================================

class TestReclamarEvento(unittest.TestCase):

    def test_reclama_evento_con_skip_locked(self):
        fila = _trabajo_base()

        fake_engine = FakeEngine(
            [
                FakeResult(
                    row=fila
                )
            ]
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "WORKER_ID",
                "audit-unit-a",
            ),
        ):
            trabajo = (
                worker.reclamar_evento()
            )

        self.assertEqual(
            trabajo,
            fila,
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "FOR UPDATE SKIP LOCKED",
            llamada["sql"],
        )

        self.assertIn(
            "estado = 'PROCESANDO'",
            llamada["sql"],
        )

        self.assertIn(
            "intentos = o.intentos + 1",
            llamada["sql"],
        )

        self.assertEqual(
            llamada[
                "params"
            ][
                "worker_id"
            ],
            "audit-unit-a",
        )

    def test_devuelve_none_si_no_hay_eventos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    row=None
                )
            ]
        )

        with patch.object(
            worker,
            "engine",
            fake_engine,
        ):
            trabajo = (
                worker.reclamar_evento()
            )

        self.assertIsNone(
            trabajo
        )


# ============================================================
# COMPLETADO
# ============================================================

class TestMarcarCompletado(unittest.TestCase):

    def test_completa_solo_trabajo_del_worker(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=1
                )
            ]
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "WORKER_ID",
                "audit-unit-a",
            ),
        ):
            actualizado = (
                worker.marcar_completado(
                    101
                )
            )

        self.assertTrue(
            actualizado
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "estado = 'COMPLETADO'",
            llamada["sql"],
        )

        self.assertIn(
            "worker_id = :worker_id",
            llamada["sql"],
        )

        self.assertEqual(
            llamada[
                "params"
            ][
                "worker_id"
            ],
            "audit-unit-a",
        )

    def test_retorna_false_si_perdio_propiedad(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=0
                )
            ]
        )

        with patch.object(
            worker,
            "engine",
            fake_engine,
        ):
            actualizado = (
                worker.marcar_completado(
                    101
                )
            )

        self.assertFalse(
            actualizado
        )


# ============================================================
# REINTENTOS / FALLIDO
# ============================================================

class TestMarcarError(unittest.TestCase):

    def test_reintenta_si_quedan_intentos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=1
                )
            ]
        )

        trabajo = _trabajo_base(
            intentos=2
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "WORKER_ID",
                "audit-unit-a",
            ),
            patch.object(
                worker,
                "MAX_ATTEMPTS",
                5,
            ),
            patch.object(
                worker,
                "RETRY_DELAY_SECONDS",
                9,
            ),
        ):
            actualizado = (
                worker.marcar_error(
                    trabajo,
                    "AUDIT_SERVICE_NO_DISPONIBLE",
                )
            )

        self.assertTrue(
            actualizado
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "estado = 'PENDIENTE'",
            llamada["sql"],
        )

        self.assertIn(
            "worker_id = NULL",
            llamada["sql"],
        )

        self.assertEqual(
            llamada[
                "params"
            ][
                "retry_seconds"
            ],
            9,
        )

    def test_pasa_a_fallido_al_agotar_intentos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=1
                )
            ]
        )

        trabajo = _trabajo_base(
            intentos=5
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "WORKER_ID",
                "audit-unit-a",
            ),
            patch.object(
                worker,
                "MAX_ATTEMPTS",
                5,
            ),
        ):
            actualizado = (
                worker.marcar_error(
                    trabajo,
                    "AUDIT_SERVICE_NO_DISPONIBLE",
                )
            )

        self.assertTrue(
            actualizado
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "estado = 'FALLIDO'",
            llamada["sql"],
        )

    def test_error_se_limita_a_500_caracteres(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=1
                )
            ]
        )

        trabajo = _trabajo_base(
            intentos=1
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "WORKER_ID",
                "audit-unit-a",
            ),
        ):
            worker.marcar_error(
                trabajo,
                "X" * 800,
            )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertEqual(
            len(
                llamada[
                    "params"
                ][
                    "error"
                ]
            ),
            500,
        )


# ============================================================
# RECUPERACIÓN DE TRABAJOS INTERRUMPIDOS
# ============================================================

class TestRecuperacion(unittest.TestCase):

    def test_recupera_trabajos_interrumpidos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(
                    rowcount=3
                )
            ]
        )

        with (
            patch.object(
                worker,
                "engine",
                fake_engine,
            ),
            patch.object(
                worker,
                "MAX_ATTEMPTS",
                5,
            ),
            patch.object(
                worker,
                "JOB_TIMEOUT_SECONDS",
                45,
            ),
        ):
            recuperados = (
                worker.recuperar_interrumpidos()
            )

        self.assertEqual(
            recuperados,
            3,
        )

        llamada = (
            fake_engine
            .connection
            .calls[0]
        )

        self.assertIn(
            "estado = CASE",
            llamada["sql"],
        )

        self.assertIn(
            "'FALLIDO'",
            llamada["sql"],
        )

        self.assertIn(
            "'PENDIENTE'",
            llamada["sql"],
        )

        self.assertEqual(
            llamada[
                "params"
            ][
                "timeout_seconds"
            ],
            45,
        )


# ============================================================
# PROCESAMIENTO
# ============================================================

class TestProcesarEvento(unittest.TestCase):

    def test_entrega_exitosa_marca_completado(self):
        trabajo = _trabajo_base()

        with (
            patch.object(
                worker,
                "enviar_evento",
                return_value=(
                    True,
                    "OK",
                ),
            ) as enviar,
            patch.object(
                worker,
                "marcar_completado",
                return_value=True,
            ) as completar,
        ):
            worker.procesar(
                trabajo
            )

        enviar.assert_called_once()
        completar.assert_called_once_with(
            101
        )

        evento_enviado = (
            enviar.call_args.args[0]
        )

        self.assertEqual(
            evento_enviado[
                "evento_uuid"
            ],
            trabajo[
                "evento_uuid"
            ],
        )

        self.assertEqual(
            evento_enviado[
                "evento"
            ],
            "LOGIN_FALLIDO",
        )

    def test_entrega_fallida_programa_reintento(self):
        trabajo = _trabajo_base()

        with (
            patch.object(
                worker,
                "enviar_evento",
                return_value=(
                    False,
                    "AUDIT_SERVICE_NO_DISPONIBLE",
                ),
            ),
            patch.object(
                worker,
                "marcar_error",
                return_value=True,
            ) as marcar_error,
        ):
            worker.procesar(
                trabajo
            )

        marcar_error.assert_called_once_with(
            trabajo,
            "AUDIT_SERVICE_NO_DISPONIBLE",
        )


# ============================================================
# ESPERA DE POSTGRESQL
# ============================================================

class TestEsperaBaseDatos(unittest.TestCase):

    def test_reintenta_y_luego_conecta(self):
        with (
            patch.object(
                worker,
                "detener",
                False,
            ),
            patch.object(
                worker,
                "verificar_conexion",
                side_effect=[
                    RuntimeError(
                        "DB no disponible"
                    ),
                    None,
                ],
            ) as verificar,
            patch.object(
                worker.time,
                "sleep",
            ) as dormir,
        ):
            conectado = (
                worker.esperar_base_datos()
            )

        self.assertTrue(
            conectado
        )

        self.assertEqual(
            verificar.call_count,
            2,
        )

        dormir.assert_called_once_with(
            5
        )

    def test_no_conecta_si_ya_recibio_apagado(self):
        with (
            patch.object(
                worker,
                "detener",
                True,
            ),
            patch.object(
                worker,
                "verificar_conexion",
            ) as verificar,
        ):
            conectado = (
                worker.esperar_base_datos()
            )

        self.assertFalse(
            conectado
        )

        verificar.assert_not_called()


# ============================================================
# SEÑAL DE APAGADO
# ============================================================

class TestSenalApagado(unittest.TestCase):

    def test_manejar_senal_activa_detencion(self):
        valor_original = (
            worker.detener
        )

        try:
            worker.detener = False

            worker.manejar_senal(
                15,
                None,
            )

            self.assertTrue(
                worker.detener
            )

        finally:
            worker.detener = (
                valor_original
            )


# ============================================================
# CLIENTE HTTP INTERNO
# ============================================================

class TestAuditClient(unittest.TestCase):

    def test_rechaza_esquemas_y_credenciales_antes_de_conectar(self):
        for url in ("file:///tmp/eventos", "ftp://host/eventos",
                    "http://user:pass@host/eventos", "http://host/eventos#fragment"):
            with self.subTest(url=url), patch.object(audit_client, "HTTPConnection") as connect:
                with self.assertRaises(ValueError):
                    with audit_client.urlopen(audit_client.Request(url), timeout=2):
                        pass
                connect.assert_not_called()

    def test_redireccion_no_se_sigue_y_conexion_se_cierra(self):
        with patch.object(audit_client, "HTTPConnection") as connect:
            connection = connect.return_value
            connection.getresponse.return_value.status = 302
            with audit_client.urlopen(audit_client.Request("http://audit/eventos"), timeout=2) as response:
                self.assertEqual(response.status, 302)
            connection.request.assert_called_once()
            connection.close.assert_called_once()

    def test_https_usa_conexion_tls(self):
        with patch.object(audit_client, "HTTPSConnection") as connect:
            connect.return_value.getresponse.return_value.status = 201
            with audit_client.urlopen(audit_client.Request("https://audit/eventos"), timeout=2):
                pass
            connect.assert_called_once_with("audit", port=None, timeout=2)
            connect.return_value.close.assert_called_once()

    def test_http_201_es_exito(self):
        with patch.object(
            audit_client,
            "urlopen",
            return_value=FakeHTTPResponse(
                201
            ),
        ):
            exito, codigo = (
                audit_client.enviar_evento(
                    {
                        "evento_uuid":
                            "11111111-1111-4111-8111-111111111111",

                        "evento":
                            "PRUEBA",
                    }
                )
            )

        self.assertTrue(
            exito
        )

        self.assertEqual(
            codigo,
            "OK",
        )

    def test_http_error_devuelve_codigo_seguro(self):
        error = HTTPError(
            url="http://audit-service-test",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )

        with patch.object(
            audit_client,
            "urlopen",
            side_effect=error,
        ):
            exito, codigo = (
                audit_client.enviar_evento(
                    {
                        "evento":
                            "PRUEBA"
                    }
                )
            )

        self.assertFalse(
            exito
        )

        self.assertEqual(
            codigo,
            "HTTP_503",
        )

    def test_error_red_devuelve_codigo_seguro(self):
        with patch.object(
            audit_client,
            "urlopen",
            side_effect=URLError(
                "error simulado"
            ),
        ):
            exito, codigo = (
                audit_client.enviar_evento(
                    {
                        "evento":
                            "PRUEBA"
                    }
                )
            )

        self.assertFalse(
            exito
        )

        self.assertEqual(
            codigo,
            "AUDIT_SERVICE_NO_DISPONIBLE",
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
