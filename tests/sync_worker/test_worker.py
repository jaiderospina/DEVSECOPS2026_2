from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "servicios" / "sync-service"

os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password_not_real"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_db"
os.environ["SYNC_POLL_SECONDS"] = "1"
os.environ["SYNC_RETRY_DELAY_SECONDS"] = "1"
os.environ["SYNC_JOB_TIMEOUT_SECONDS"] = "30"
os.environ["SYNC_RECOVERY_CHECK_SECONDS"] = "30"
os.environ["SYNC_SIMULATED_PROCESS_SECONDS"] = "1"
os.environ["SYNC_WORKER_ID"] = "sync-test-worker"

if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


def _cargar_modulo(nombre: str, ruta: Path):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No fue posible cargar el módulo de prueba: {nombre}")

    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


sys.modules.pop("database", None)
database = _cargar_modulo("database", SERVICE_DIR / "database.py")
worker = _cargar_modulo("iam_sync_worker_main", SERVICE_DIR / "main.py")


class FakeMappings:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class FakeResult:
    def __init__(self, row=None, rowcount=0):
        self._row = row
        self.rowcount = rowcount

    def mappings(self):
        return FakeMappings(self._row)


class FakeConnection:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=None):
        self.calls.append({"sql": str(statement), "params": params or {}})
        if not self._results:
            raise AssertionError("La prueba ejecutó más consultas SQL de las esperadas")
        return self._results.pop(0)


class FakeEngine:
    def __init__(self, results):
        self.connection = FakeConnection(results)

    def begin(self):
        return self.connection

    def connect(self):
        return self.connection


class FakeEvent:
    def __init__(self, initially_set=False):
        self._set = initially_set
        self.wait_calls = []

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    def wait(self, seconds):
        self.wait_calls.append(seconds)
        return self._set


class TestConfiguracionWorker(unittest.TestCase):
    def test_entero_positivo_acepta_valor_valido(self):
        with patch.dict(os.environ, {"SYNC_TEST_INTEGER": "7"}, clear=False):
            self.assertEqual(worker._entero_positivo("SYNC_TEST_INTEGER", 5), 7)

    def test_entero_positivo_rechaza_texto(self):
        with patch.dict(os.environ, {"SYNC_TEST_INTEGER": "abc"}, clear=False):
            with self.assertRaises(RuntimeError):
                worker._entero_positivo("SYNC_TEST_INTEGER", 5)

    def test_entero_positivo_rechaza_cero(self):
        with patch.dict(os.environ, {"SYNC_TEST_INTEGER": "0"}, clear=False):
            with self.assertRaises(RuntimeError):
                worker._entero_positivo("SYNC_TEST_INTEGER", 5)


class TestValidacionObjetivo(unittest.TestCase):
    def test_rechaza_trabajo_sin_usuario(self):
        with self.assertRaisesRegex(worker.ErrorTrabajoSync, "identidad objetivo"):
            worker.validar_objetivo({"usuario_id": None, "compania_id": None})

    def test_rechaza_usuario_inexistente(self):
        fake_engine = FakeEngine([FakeResult(row=None)])
        with patch.object(worker, "engine", fake_engine):
            with self.assertRaisesRegex(worker.ErrorTrabajoSync, "identidad objetivo no existe"):
                worker.validar_objetivo({"usuario_id": 999, "compania_id": None})

    def test_rechaza_compania_inexistente(self):
        fake_engine = FakeEngine(
            [
                FakeResult(row={"id": 34, "activo": True}),
                FakeResult(row=None),
            ]
        )
        with patch.object(worker, "engine", fake_engine):
            with self.assertRaisesRegex(worker.ErrorTrabajoSync, "compañía objetivo no existe"):
                worker.validar_objetivo({"usuario_id": 34, "compania_id": 999})

    def test_acepta_objetivo_existente(self):
        fake_engine = FakeEngine(
            [
                FakeResult(row={"id": 34, "activo": True}),
                FakeResult(row={"id": 6, "activo": True}),
            ]
        )
        with patch.object(worker, "engine", fake_engine):
            worker.validar_objetivo({"usuario_id": 34, "compania_id": 6})
        self.assertEqual(len(fake_engine.connection.calls), 2)


class TestConectorSimulado(unittest.TestCase):
    def test_soporta_las_cuatro_operaciones(self):
        operaciones = ("PROVISIONAR", "MODIFICAR", "DESHABILITAR", "REVOCAR")

        with patch.object(worker, "validar_objetivo") as validar, patch.object(worker.time, "sleep") as dormir:
            for operacion in operaciones:
                with self.subTest(operacion=operacion):
                    resultado = worker.ejecutar_conector_simulado(
                        {"operacion": operacion, "usuario_id": 34, "compania_id": 6}
                    )
                    self.assertIn(operacion, resultado)

            self.assertEqual(validar.call_count, 4)
            self.assertEqual(dormir.call_count, 4)

    def test_rechaza_operacion_no_soportada(self):
        with self.assertRaisesRegex(worker.ErrorTrabajoSync, "no está soportada"):
            worker.ejecutar_conector_simulado(
                {"operacion": "OPERACION_INVALIDA", "usuario_id": 34, "compania_id": 6}
            )


class TestReclamarTrabajo(unittest.TestCase):
    def test_reclama_job_y_usa_skip_locked(self):
        fila = {
            "id": 101,
            "operacion": "MODIFICAR",
            "usuario_id": 34,
            "compania_id": 6,
            "solicitado_por_usuario_id": 18,
            "intentos": 1,
            "max_intentos": 3,
        }
        fake_engine = FakeEngine([FakeResult(row=fila)])

        with patch.object(worker, "engine", fake_engine), patch.object(worker, "WORKER_ID", "sync-unit-a"):
            trabajo = worker.reclamar_siguiente_trabajo()

        self.assertEqual(trabajo, fila)
        llamada = fake_engine.connection.calls[0]
        self.assertIn("FOR UPDATE SKIP LOCKED", llamada["sql"])
        self.assertIn("estado = 'PROCESANDO'", llamada["sql"])
        self.assertEqual(llamada["params"]["worker_id"], "sync-unit-a")

    def test_devuelve_none_cuando_no_hay_jobs(self):
        fake_engine = FakeEngine([FakeResult(row=None)])
        with patch.object(worker, "engine", fake_engine):
            trabajo = worker.reclamar_siguiente_trabajo()
        self.assertIsNone(trabajo)


class TestMarcarCompletado(unittest.TestCase):
    def test_finaliza_solo_job_del_worker_actual(self):
        fake_engine = FakeEngine([FakeResult(rowcount=1)])
        resultado_extenso = "X" * 800

        with patch.object(worker, "engine", fake_engine), patch.object(worker, "WORKER_ID", "sync-unit-a"):
            actualizado = worker.marcar_completado(101, resultado_extenso)

        self.assertTrue(actualizado)
        llamada = fake_engine.connection.calls[0]
        self.assertIn("estado = 'COMPLETADO'", llamada["sql"])
        self.assertIn("worker_id = :worker_id", llamada["sql"])
        self.assertEqual(llamada["params"]["worker_id"], "sync-unit-a")
        self.assertEqual(len(llamada["params"]["resultado"]), 500)

    def test_retorna_false_si_job_ya_no_pertenece_al_worker(self):
        fake_engine = FakeEngine([FakeResult(rowcount=0)])
        with patch.object(worker, "engine", fake_engine):
            actualizado = worker.marcar_completado(101, "resultado")
        self.assertFalse(actualizado)


class TestRegistrarFallo(unittest.TestCase):
    def test_reintenta_si_quedan_intentos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(row={"intentos": 1, "max_intentos": 3}),
                FakeResult(rowcount=1),
            ]
        )

        with patch.object(worker, "engine", fake_engine),              patch.object(worker, "WORKER_ID", "sync-unit-a"),              patch.object(worker, "SYNC_RETRY_DELAY_SECONDS", 9):
            estado = worker.registrar_fallo(101, "Fallo funcional controlado")

        self.assertEqual(estado, "REINTENTO")
        actualizacion = fake_engine.connection.calls[1]
        self.assertIn("estado = 'PENDIENTE'", actualizacion["sql"])
        self.assertIn("worker_id = NULL", actualizacion["sql"])
        self.assertEqual(actualizacion["params"]["retry_delay"], 9)

    def test_pasa_a_fallido_al_agotar_intentos(self):
        fake_engine = FakeEngine(
            [
                FakeResult(row={"intentos": 3, "max_intentos": 3}),
                FakeResult(rowcount=1),
            ]
        )

        with patch.object(worker, "engine", fake_engine), patch.object(worker, "WORKER_ID", "sync-unit-a"):
            estado = worker.registrar_fallo(101, "Fallo funcional controlado")

        self.assertEqual(estado, "FALLIDO")
        actualizacion = fake_engine.connection.calls[1]
        self.assertIn("estado = 'FALLIDO'", actualizacion["sql"])

    def test_retorna_no_encontrado_si_no_es_duenio_del_job(self):
        fake_engine = FakeEngine([FakeResult(row=None)])
        with patch.object(worker, "engine", fake_engine):
            estado = worker.registrar_fallo(101, "Fallo funcional controlado")

        self.assertEqual(estado, "NO_ENCONTRADO")
        self.assertEqual(len(fake_engine.connection.calls), 1)


class TestRecuperacion(unittest.TestCase):
    def test_recupera_jobs_interrumpidos(self):
        fake_engine = FakeEngine([FakeResult(rowcount=2)])

        with patch.object(worker, "engine", fake_engine), patch.object(worker, "SYNC_JOB_TIMEOUT_SECONDS", 45):
            recuperados = worker.recuperar_trabajos_interrumpidos()

        self.assertEqual(recuperados, 2)
        llamada = fake_engine.connection.calls[0]
        self.assertIn("estado = CASE", llamada["sql"])
        self.assertIn("'FALLIDO'", llamada["sql"])
        self.assertIn("'PENDIENTE'", llamada["sql"])
        self.assertEqual(llamada["params"]["timeout_seconds"], 45)


class TestProcesarTrabajo(unittest.TestCase):
    def setUp(self):
        self.trabajo = {
            "id": 101,
            "operacion": "MODIFICAR",
            "usuario_id": 34,
            "compania_id": 6,
            "solicitado_por_usuario_id": 18,
            "intentos": 1,
            "max_intentos": 3,
        }

    def test_procesamiento_exitoso_marca_completado(self):
        with patch.object(worker, "ejecutar_conector_simulado", return_value="resultado seguro") as conector,              patch.object(worker, "marcar_completado", return_value=True) as completar:
            worker.procesar_trabajo(dict(self.trabajo))

        conector.assert_called_once()
        completar.assert_called_once_with(101, "resultado seguro")

    def test_error_funcional_se_registra_como_reintento(self):
        with patch.object(
            worker,
            "ejecutar_conector_simulado",
            side_effect=worker.ErrorTrabajoSync("Error funcional seguro"),
        ), patch.object(worker, "registrar_fallo", return_value="REINTENTO") as registrar:
            worker.procesar_trabajo(dict(self.trabajo))

        registrar.assert_called_once_with(101, "Error funcional seguro")

    def test_error_inesperado_no_persiste_mensaje_bruto(self):
        mensaje_sensible_simulado = "PASSWORD=NO_ES_REAL_SOLO_PRUEBA"

        with patch.object(
            worker,
            "ejecutar_conector_simulado",
            side_effect=RuntimeError(mensaje_sensible_simulado),
        ), patch.object(
            worker,
            "registrar_fallo",
            return_value="REINTENTO",
        ) as registrar, patch.object(worker.logger, "error") as log_error:
            worker.procesar_trabajo(dict(self.trabajo))

        registrar.assert_called_once_with(
            101,
            "Error interno durante el procesamiento del trabajo",
        )
        self.assertNotIn(mensaje_sensible_simulado, str(log_error.call_args))


class TestEsperaBaseDatos(unittest.TestCase):
    def test_reintenta_y_luego_conecta(self):
        evento = FakeEvent()

        with patch.object(worker, "detener_worker", evento), patch.object(
            worker,
            "verificar_conexion",
            side_effect=[RuntimeError("DB no disponible"), None],
        ) as verificar:
            conectado = worker.esperar_base_datos()

        self.assertTrue(conectado)
        self.assertEqual(verificar.call_count, 2)
        self.assertEqual(evento.wait_calls, [worker.SYNC_POLL_SECONDS])

    def test_no_intenta_conectar_si_ya_recibio_apagado(self):
        evento = FakeEvent(initially_set=True)

        with patch.object(worker, "detener_worker", evento), patch.object(
            worker,
            "verificar_conexion",
        ) as verificar:
            conectado = worker.esperar_base_datos()

        self.assertFalse(conectado)
        verificar.assert_not_called()


class TestSenalApagado(unittest.TestCase):
    def test_manejar_senal_activa_evento_de_salida(self):
        evento = FakeEvent()

        with patch.object(worker, "detener_worker", evento):
            worker._manejar_senal(15, None)

        self.assertTrue(evento.is_set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
