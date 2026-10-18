import logging
import os
import signal
import socket
import threading
import time
from typing import Any

from sqlalchemy import text

from database import engine, verificar_conexion


# ============================================================
# IAM SECURE - SYNC WORKER
# ============================================================
#
# Proceso asíncrono independiente encargado de consumir trabajos
# persistidos en PostgreSQL.
#
# FLUJO:
#
# PENDIENTE
#     ↓
# PROCESANDO
#     ↓
# ├── COMPLETADO
# └── PENDIENTE nuevamente si corresponde reintentar
#         ↓
#       FALLIDO al agotar el máximo de intentos
#
# SEGURIDAD:
# - No consume ni registra contraseñas.
# - No consume ni registra hashes.
# - No consume ni registra JWT/JTI.
# - No consume ni registra secretos MFA/TOTP.
# - No registra cadenas de conexión.
# ============================================================


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    ),
)

logger = logging.getLogger("iam-secure-sync-worker")


# ============================================================
# CONFIGURACIÓN
# ============================================================


def _entero_positivo(
    nombre: str,
    valor_predeterminado: int,
) -> int:
    """
    Obtiene una configuración entera positiva.

    El mensaje de error nunca incluye valores sensibles.
    """
    valor = os.getenv(
        nombre,
        str(valor_predeterminado),
    )

    try:
        numero = int(valor)
    except ValueError as exc:
        raise RuntimeError(
            f"{nombre} debe ser un número entero válido"
        ) from exc

    if numero <= 0:
        raise RuntimeError(
            f"{nombre} debe ser mayor que cero"
        )

    return numero


SYNC_POLL_SECONDS = _entero_positivo(
    "SYNC_POLL_SECONDS",
    5,
)

SYNC_RETRY_DELAY_SECONDS = _entero_positivo(
    "SYNC_RETRY_DELAY_SECONDS",
    15,
)

SYNC_JOB_TIMEOUT_SECONDS = _entero_positivo(
    "SYNC_JOB_TIMEOUT_SECONDS",
    300,
)

SYNC_RECOVERY_CHECK_SECONDS = _entero_positivo(
    "SYNC_RECOVERY_CHECK_SECONDS",
    60,
)

SYNC_SIMULATED_PROCESS_SECONDS = _entero_positivo(
    "SYNC_SIMULATED_PROCESS_SECONDS",
    2,
)


# ============================================================
# IDENTIDAD DEL WORKER
# ============================================================
#
# El identificador permite conocer qué instancia tomó un trabajo.
# No representa una credencial.
# ============================================================

WORKER_ID = (
    os.getenv("SYNC_WORKER_ID")
    or f"sync-{socket.gethostname()}"
).strip()[:100]

if not WORKER_ID:
    WORKER_ID = "sync-worker"


# ============================================================
# CONTROL DE APAGADO
# ============================================================

detener_worker = threading.Event()


def _manejar_senal(
    numero_senal: int,
    _frame: Any,
) -> None:
    """
    Permite terminar correctamente el proceso cuando Docker envía
    SIGTERM o cuando el usuario interrumpe la ejecución.
    """
    logger.info(
        "Señal de apagado recibida signal=%s",
        numero_senal,
    )

    detener_worker.set()


signal.signal(
    signal.SIGTERM,
    _manejar_senal,
)

signal.signal(
    signal.SIGINT,
    _manejar_senal,
)


# ============================================================
# ERROR CONTROLADO DEL TRABAJO
# ============================================================


class ErrorTrabajoSync(Exception):
    """
    Error funcional cuyo mensaje es seguro para almacenarse en
    sync_jobs.ultimo_error.
    """


# ============================================================
# RECLAMAR UN TRABAJO
# ============================================================


def reclamar_siguiente_trabajo() -> dict | None:
    """
    Reclama atómicamente un único trabajo pendiente.

    FOR UPDATE SKIP LOCKED evita que dos instancias del worker
    seleccionen simultáneamente el mismo trabajo.

    La transacción cambia inmediatamente el estado a PROCESANDO
    antes de liberar el bloqueo.
    """

    consulta = text(
        """
        WITH siguiente AS (
            SELECT id
            FROM sync_jobs
            WHERE estado = 'PENDIENTE'
              AND disponible_desde <= NOW()
              AND intentos < max_intentos
            ORDER BY
                disponible_desde ASC,
                id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE sync_jobs AS trabajo
        SET
            estado = 'PROCESANDO',
            intentos = trabajo.intentos + 1,
            worker_id = :worker_id,
            fecha_inicio = COALESCE(
                trabajo.fecha_inicio,
                NOW()
            ),
            fecha_actualizacion = NOW(),
            ultimo_error = NULL
        FROM siguiente
        WHERE trabajo.id = siguiente.id
        RETURNING
            trabajo.id,
            trabajo.operacion,
            trabajo.usuario_id,
            trabajo.compania_id,
            trabajo.solicitado_por_usuario_id,
            trabajo.intentos,
            trabajo.max_intentos
        """
    )

    with engine.begin() as conexion:
        fila = conexion.execute(
            consulta,
            {
                "worker_id": WORKER_ID,
            },
        ).mappings().first()

    if fila is None:
        return None

    return dict(fila)


# ============================================================
# VALIDACIÓN DEL OBJETIVO
# ============================================================


def validar_objetivo(
    trabajo: dict,
) -> None:
    """
    Comprueba que la identidad y, cuando corresponde, la compañía
    continúen existiendo.

    Solo consulta identificadores y estado operativo.
    No consulta credenciales.
    """

    usuario_id = trabajo.get("usuario_id")

    if usuario_id is None:
        raise ErrorTrabajoSync(
            "La identidad objetivo ya no está disponible"
        )

    with engine.connect() as conexion:
        usuario = conexion.execute(
            text(
                """
                SELECT
                    id,
                    activo
                FROM usuarios_plataforma
                WHERE id = :usuario_id
                """
            ),
            {
                "usuario_id": usuario_id,
            },
        ).mappings().first()

        if usuario is None:
            raise ErrorTrabajoSync(
                "La identidad objetivo no existe"
            )

        compania_id = trabajo.get("compania_id")

        if compania_id is not None:
            compania = conexion.execute(
                text(
                    """
                    SELECT
                        id,
                        activo
                    FROM companias
                    WHERE id = :compania_id
                    """
                ),
                {
                    "compania_id": compania_id,
                },
            ).mappings().first()

            if compania is None:
                raise ErrorTrabajoSync(
                    "La compañía objetivo no existe"
                )


# ============================================================
# CONECTOR SIMULADO
# ============================================================
#
# Esta primera versión demuestra el patrón asíncrono requerido
# por el proyecto académico.
#
# Posteriormente este punto podrá sustituirse por adaptadores a:
# - directorios corporativos;
# - aplicaciones empresariales;
# - APIs externas;
# - otros sistemas IAM.
#
# El worker no recibe credenciales de usuario final.
# ============================================================


def ejecutar_conector_simulado(
    trabajo: dict,
) -> str:
    """
    Ejecuta una operación simulada de sincronización.
    """

    operacion = trabajo["operacion"]

    operaciones_soportadas = {
        "PROVISIONAR",
        "MODIFICAR",
        "DESHABILITAR",
        "REVOCAR",
    }

    if operacion not in operaciones_soportadas:
        raise ErrorTrabajoSync(
            "La operación solicitada no está soportada"
        )

    validar_objetivo(trabajo)

    # --------------------------------------------------------
    # SIMULACIÓN CONTROLADA
    # --------------------------------------------------------
    #
    # Representa una llamada futura hacia un sistema externo.
    # No se generan ni manipulan secretos.
    # --------------------------------------------------------

    time.sleep(
        SYNC_SIMULATED_PROCESS_SECONDS
    )

    return (
        f"Operación {operacion} procesada correctamente "
        "por el conector simulado"
    )


# ============================================================
# MARCAR TRABAJO COMO COMPLETADO
# ============================================================


def marcar_completado(
    trabajo_id: int,
    resultado: str,
) -> bool:
    """
    Finaliza un trabajo únicamente si todavía pertenece a esta
    instancia del worker.
    """

    consulta = text(
        """
        UPDATE sync_jobs
        SET
            estado = 'COMPLETADO',
            resultado = :resultado,
            ultimo_error = NULL,
            fecha_fin = NOW(),
            fecha_actualizacion = NOW()
        WHERE id = :trabajo_id
          AND estado = 'PROCESANDO'
          AND worker_id = :worker_id
        """
    )

    with engine.begin() as conexion:
        resultado_sql = conexion.execute(
            consulta,
            {
                "trabajo_id": trabajo_id,
                "worker_id": WORKER_ID,
                "resultado": resultado[:500],
            },
        )

    return resultado_sql.rowcount == 1


# ============================================================
# GESTIONAR ERROR / REINTENTO
# ============================================================


def registrar_fallo(
    trabajo_id: int,
    mensaje_seguro: str,
) -> str:
    """
    Determina de forma transaccional si el trabajo debe volver a
    PENDIENTE o quedar definitivamente FALLIDO.

    Nunca almacena el mensaje bruto de una excepción inesperada.
    """

    mensaje_seguro = mensaje_seguro[:1000]

    with engine.begin() as conexion:
        trabajo = conexion.execute(
            text(
                """
                SELECT
                    intentos,
                    max_intentos
                FROM sync_jobs
                WHERE id = :trabajo_id
                  AND estado = 'PROCESANDO'
                  AND worker_id = :worker_id
                FOR UPDATE
                """
            ),
            {
                "trabajo_id": trabajo_id,
                "worker_id": WORKER_ID,
            },
        ).mappings().first()

        if trabajo is None:
            return "NO_ENCONTRADO"

        intentos = trabajo["intentos"]
        max_intentos = trabajo["max_intentos"]

        if intentos >= max_intentos:
            conexion.execute(
                text(
                    """
                    UPDATE sync_jobs
                    SET
                        estado = 'FALLIDO',
                        ultimo_error = :ultimo_error,
                        fecha_fin = NOW(),
                        fecha_actualizacion = NOW()
                    WHERE id = :trabajo_id
                      AND estado = 'PROCESANDO'
                      AND worker_id = :worker_id
                    """
                ),
                {
                    "trabajo_id": trabajo_id,
                    "worker_id": WORKER_ID,
                    "ultimo_error": mensaje_seguro,
                },
            )

            return "FALLIDO"

        conexion.execute(
            text(
                """
                UPDATE sync_jobs
                SET
                    estado = 'PENDIENTE',
                    worker_id = NULL,
                    ultimo_error = :ultimo_error,
                    resultado = NULL,
                    disponible_desde =
                        NOW()
                        + (
                            :retry_delay
                            * INTERVAL '1 second'
                        ),
                    fecha_actualizacion = NOW()
                WHERE id = :trabajo_id
                  AND estado = 'PROCESANDO'
                  AND worker_id = :worker_id
                """
            ),
            {
                "trabajo_id": trabajo_id,
                "worker_id": WORKER_ID,
                "ultimo_error": mensaje_seguro,
                "retry_delay": (
                    SYNC_RETRY_DELAY_SECONDS
                ),
            },
        )

        return "REINTENTO"


# ============================================================
# RECUPERAR TRABAJOS INTERRUMPIDOS
# ============================================================
#
# Si una instancia termina abruptamente después de reclamar un
# trabajo, el registro podría permanecer en PROCESANDO.
#
# Después del tiempo configurado se recupera:
#
# - vuelve a PENDIENTE si aún tiene intentos disponibles;
# - pasa a FALLIDO si ya agotó su máximo.
# ============================================================


def recuperar_trabajos_interrumpidos() -> int:
    consulta = text(
        """
        UPDATE sync_jobs
        SET
            estado = CASE
                WHEN intentos >= max_intentos
                    THEN 'FALLIDO'
                ELSE 'PENDIENTE'
            END,

            worker_id = NULL,

            disponible_desde = CASE
                WHEN intentos >= max_intentos
                    THEN disponible_desde
                ELSE NOW()
            END,

            ultimo_error =
                'Trabajo recuperado después de una interrupción del worker',

            fecha_fin = CASE
                WHEN intentos >= max_intentos
                    THEN NOW()
                ELSE NULL
            END,

            fecha_actualizacion = NOW()

        WHERE estado = 'PROCESANDO'
          AND fecha_actualizacion <
              NOW()
              - (
                  :timeout_seconds
                  * INTERVAL '1 second'
              )
        """
    )

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "timeout_seconds":
                    SYNC_JOB_TIMEOUT_SECONDS,
            },
        )

    return resultado.rowcount


# ============================================================
# PROCESAR TRABAJO
# ============================================================


def procesar_trabajo(
    trabajo: dict,
) -> None:
    trabajo_id = trabajo["id"]

    logger.info(
        (
            "Trabajo reclamado "
            "job_id=%s operacion=%s intento=%s/%s"
        ),
        trabajo_id,
        trabajo["operacion"],
        trabajo["intentos"],
        trabajo["max_intentos"],
    )

    try:
        resultado = ejecutar_conector_simulado(
            trabajo
        )

        actualizado = marcar_completado(
            trabajo_id,
            resultado,
        )

        if actualizado:
            logger.info(
                "Trabajo completado job_id=%s",
                trabajo_id,
            )
        else:
            logger.warning(
                (
                    "No fue posible finalizar el trabajo "
                    "porque su estado cambió job_id=%s"
                ),
                trabajo_id,
            )

    except ErrorTrabajoSync as exc:
        estado = registrar_fallo(
            trabajo_id,
            str(exc),
        )

        logger.warning(
            (
                "Fallo funcional job_id=%s "
                "resultado=%s"
            ),
            trabajo_id,
            estado,
        )

    except Exception as exc:
        # ----------------------------------------------------
        # SEGURIDAD
        # ----------------------------------------------------
        # No almacenamos ni imprimimos str(exc) porque una
        # excepción inesperada podría contener información
        # interna, parámetros o datos sensibles.
        # ----------------------------------------------------

        estado = registrar_fallo(
            trabajo_id,
            "Error interno durante el procesamiento del trabajo",
        )

        logger.error(
            (
                "Error interno job_id=%s "
                "tipo=%s resultado=%s"
            ),
            trabajo_id,
            type(exc).__name__,
            estado,
        )


# ============================================================
# ESPERAR POSTGRESQL
# ============================================================


def esperar_base_datos() -> bool:
    """
    Espera hasta que PostgreSQL esté disponible o hasta recibir
    una señal de apagado.
    """

    while not detener_worker.is_set():
        try:
            verificar_conexion()

            logger.info(
                "Conexión con PostgreSQL verificada"
            )

            return True

        except Exception as exc:
            logger.warning(
                (
                    "PostgreSQL no disponible "
                    "tipo=%s; nuevo intento en %s segundos"
                ),
                type(exc).__name__,
                SYNC_POLL_SECONDS,
            )

            detener_worker.wait(
                SYNC_POLL_SECONDS
            )

    return False


# ============================================================
# BUCLE PRINCIPAL
# ============================================================


def ejecutar_worker() -> None:
    logger.info(
        "Sync Worker iniciando worker_id=%s",
        WORKER_ID,
    )

    if not esperar_base_datos():
        return

    recuperados = recuperar_trabajos_interrumpidos()

    if recuperados:
        logger.warning(
            "Trabajos interrumpidos recuperados cantidad=%s",
            recuperados,
        )

    ultimo_control_recuperacion = time.monotonic()

    logger.info(
        "Sync Worker listo para procesar trabajos"
    )

    while not detener_worker.is_set():

        # ----------------------------------------------------
        # RECUPERACIÓN PERIÓDICA
        # ----------------------------------------------------

        ahora_monotonic = time.monotonic()

        if (
            ahora_monotonic
            - ultimo_control_recuperacion
            >= SYNC_RECOVERY_CHECK_SECONDS
        ):
            try:
                recuperados = (
                    recuperar_trabajos_interrumpidos()
                )

                if recuperados:
                    logger.warning(
                        (
                            "Trabajos interrumpidos "
                            "recuperados cantidad=%s"
                        ),
                        recuperados,
                    )

            except Exception as exc:
                logger.error(
                    (
                        "Error durante recuperación "
                        "tipo=%s"
                    ),
                    type(exc).__name__,
                )

            ultimo_control_recuperacion = (
                ahora_monotonic
            )

        # ----------------------------------------------------
        # TOMAR EL SIGUIENTE TRABAJO
        # ----------------------------------------------------

        try:
            trabajo = reclamar_siguiente_trabajo()

        except Exception as exc:
            logger.error(
                (
                    "Error consultando la cola "
                    "tipo=%s"
                ),
                type(exc).__name__,
            )

            detener_worker.wait(
                SYNC_POLL_SECONDS
            )

            continue

        if trabajo is None:
            detener_worker.wait(
                SYNC_POLL_SECONDS
            )

            continue

        procesar_trabajo(
            trabajo
        )

    logger.info(
        "Sync Worker detenido correctamente"
    )


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    ejecutar_worker()
