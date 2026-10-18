import logging
import os
import signal
import socket
import time

from sqlalchemy import text

from audit_client import enviar_evento
from database import engine, verificar_conexion


# ============================================================
# IAM SECURE - AUDIT DISPATCHER WORKER
# ============================================================
#
# Responsabilidades:
# - reclamar eventos PENDIENTES;
# - evitar procesamiento duplicado con SKIP LOCKED;
# - entregar al Audit Service;
# - reintentar errores temporales;
# - recuperar trabajos abandonados;
# - marcar definitivamente FALLIDO cuando se agoten intentos.
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

logger = logging.getLogger(
    "iam.audit.dispatcher"
)


def _entero_positivo(
    nombre: str,
    predeterminado: int,
) -> int:
    try:
        valor = int(
            os.getenv(
                nombre,
                str(predeterminado),
            )
        )
    except ValueError as exc:
        raise RuntimeError(
            f"{nombre} debe ser entero"
        ) from exc

    if valor <= 0:
        raise RuntimeError(
            f"{nombre} debe ser mayor que cero"
        )

    return valor


POLL_SECONDS = _entero_positivo(
    "AUDIT_DISPATCH_POLL_SECONDS",
    2,
)

RETRY_DELAY_SECONDS = _entero_positivo(
    "AUDIT_DISPATCH_RETRY_DELAY_SECONDS",
    15,
)

MAX_ATTEMPTS = _entero_positivo(
    "AUDIT_DISPATCH_MAX_ATTEMPTS",
    5,
)

JOB_TIMEOUT_SECONDS = _entero_positivo(
    "AUDIT_DISPATCH_JOB_TIMEOUT_SECONDS",
    120,
)

RECOVERY_CHECK_SECONDS = _entero_positivo(
    "AUDIT_DISPATCH_RECOVERY_CHECK_SECONDS",
    30,
)

WORKER_ID = (
    os.getenv(
        "AUDIT_DISPATCH_WORKER_ID"
    )
    or socket.gethostname()
).strip()


detener = False


# ============================================================
# SENIALES
# ============================================================

def manejar_senal(
    _numero,
    _frame,
):
    global detener

    detener = True

    logger.info(
        "Solicitud de apagado recibida"
    )


signal.signal(
    signal.SIGTERM,
    manejar_senal,
)

signal.signal(
    signal.SIGINT,
    manejar_senal,
)


# ============================================================
# CLAIM ATOMICO
# ============================================================

def reclamar_evento():
    consulta = text(
        """
        WITH candidato AS (
            SELECT id
            FROM auditoria_outbox
            WHERE estado = 'PENDIENTE'
              AND disponible_desde <= NOW()
            ORDER BY disponible_desde, id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE auditoria_outbox AS o
        SET
            estado = 'PROCESANDO',
            intentos = o.intentos + 1,
            worker_id = :worker_id,
            procesando_desde = NOW(),
            actualizado_en = NOW()
        FROM candidato AS c
        WHERE o.id = c.id
        RETURNING
            o.id,
            o.evento_uuid,
            o.fecha_evento,
            o.servicio,
            o.evento,
            o.resultado,
            o.actor_usuario_id,
            o.objetivo_usuario_id,
            o.compania_id,
            o.detalle,
            o.intentos
        """
    )

    with engine.begin() as conexion:
        return conexion.execute(
            consulta,
            {
                "worker_id": WORKER_ID
            },
        ).mappings().first()


# ============================================================
# COMPLETAR
# ============================================================

def marcar_completado(
    outbox_id: int,
) -> bool:
    consulta = text(
        """
        UPDATE auditoria_outbox
        SET
            estado = 'COMPLETADO',
            completado_en = NOW(),
            actualizado_en = NOW(),
            ultimo_error = NULL
        WHERE id = :id
          AND estado = 'PROCESANDO'
          AND worker_id = :worker_id
        """
    )

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "id": outbox_id,
                "worker_id": WORKER_ID,
            },
        )

        return resultado.rowcount == 1


# ============================================================
# REINTENTO / FALLO
# ============================================================

def marcar_error(
    trabajo: dict,
    codigo_error: str,
) -> bool:

    if trabajo["intentos"] >= MAX_ATTEMPTS:
        consulta = text(
            """
            UPDATE auditoria_outbox
            SET
                estado = 'FALLIDO',
                ultimo_error = :error,
                procesando_desde = NULL,
                actualizado_en = NOW()
            WHERE id = :id
              AND estado = 'PROCESANDO'
              AND worker_id = :worker_id
            """
        )

        parametros = {
            "id": trabajo["id"],
            "worker_id": WORKER_ID,
            "error": codigo_error[:500],
        }

    else:
        consulta = text(
            """
            UPDATE auditoria_outbox
            SET
                estado = 'PENDIENTE',
                disponible_desde =
                    NOW()
                    + (
                        :retry_seconds
                        * INTERVAL '1 second'
                    ),
                ultimo_error = :error,
                worker_id = NULL,
                procesando_desde = NULL,
                actualizado_en = NOW()
            WHERE id = :id
              AND estado = 'PROCESANDO'
              AND worker_id = :worker_id
            """
        )

        parametros = {
            "id": trabajo["id"],
            "worker_id": WORKER_ID,
            "error": codigo_error[:500],
            "retry_seconds":
                RETRY_DELAY_SECONDS,
        }

    with engine.begin() as conexion:
        resultado = conexion.execute(
            consulta,
            parametros,
        )

        return resultado.rowcount == 1


# ============================================================
# RECUPERAR TRABAJOS ABANDONADOS
# ============================================================

def recuperar_interrumpidos() -> int:
    consulta = text(
        """
        UPDATE auditoria_outbox
        SET
            estado = CASE
                WHEN intentos >= :max_attempts
                    THEN 'FALLIDO'
                ELSE 'PENDIENTE'
            END,

            disponible_desde = CASE
                WHEN intentos >= :max_attempts
                    THEN disponible_desde
                ELSE NOW()
            END,

            ultimo_error =
                'WORKER_INTERRUMPIDO',

            worker_id = NULL,
            procesando_desde = NULL,
            actualizado_en = NOW()

        WHERE estado = 'PROCESANDO'
          AND procesando_desde
              < NOW()
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
                "max_attempts":
                    MAX_ATTEMPTS,

                "timeout_seconds":
                    JOB_TIMEOUT_SECONDS,
            },
        )

        return resultado.rowcount


# ============================================================
# PROCESAR EVENTO
# ============================================================

def procesar(
    trabajo,
) -> None:

    evento = {
        "evento_uuid":
            str(trabajo["evento_uuid"]),

        "fecha_evento":
            trabajo[
                "fecha_evento"
            ].isoformat(),

        "servicio":
            trabajo["servicio"],

        "evento":
            trabajo["evento"],

        "resultado":
            trabajo["resultado"],

        "actor_usuario_id":
            trabajo["actor_usuario_id"],

        "objetivo_usuario_id":
            trabajo[
                "objetivo_usuario_id"
            ],

        "compania_id":
            trabajo["compania_id"],

        "detalle":
            trabajo["detalle"] or {},
    }

    exito, codigo = enviar_evento(
        evento
    )

    if exito:
        actualizado = marcar_completado(
            trabajo["id"]
        )

        logger.info(
            (
                "Evento procesado id=%s "
                "evento=%s intento=%s "
                "actualizado=%s"
            ),
            trabajo["id"],
            trabajo["evento"],
            trabajo["intentos"],
            actualizado,
        )

        return

    actualizado = marcar_error(
        trabajo,
        codigo,
    )

    if actualizado and trabajo["intentos"] >= MAX_ATTEMPTS:
        # Terminal failure is actionable and retained in the outbox. No payload,
        # token, SQL or exception text is included in this operator alert.
        logger.error(
            "AUDIT_OUTBOX_FALLIDO id=%s intentos=%s",
            trabajo["id"], trabajo["intentos"],
        )

    logger.warning(
        (
            "Entrega fallida id=%s "
            "evento=%s intento=%s "
            "resultado=%s actualizado=%s"
        ),
        trabajo["id"],
        trabajo["evento"],
        trabajo["intentos"],
        codigo,
        actualizado,
    )


# ============================================================
# ESPERA DE POSTGRESQL
# ============================================================

def esperar_base_datos() -> bool:

    while not detener:
        try:
            verificar_conexion()

            logger.info(
                "Conexion PostgreSQL verificada"
            )

            return True

        except Exception as exc:
            logger.warning(
                (
                    "PostgreSQL no disponible "
                    "tipo=%s; reintento en 5 segundos"
                ),
                type(exc).__name__,
            )

            time.sleep(5)

    return False


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def main() -> None:
    logger.info(
        "Audit Dispatcher iniciando worker_id=%s",
        WORKER_ID,
    )

    if not esperar_base_datos():
        return

    ultima_recuperacion = 0.0

    logger.info(
        "Audit Dispatcher listo"
    )

    while not detener:

        try:
            ahora = time.monotonic()

            if (
                ahora - ultima_recuperacion
                >= RECOVERY_CHECK_SECONDS
            ):
                recuperados = (
                    recuperar_interrumpidos()
                )

                if recuperados:
                    logger.warning(
                        "Trabajos recuperados=%s",
                        recuperados,
                    )

                ultima_recuperacion = ahora

            trabajo = reclamar_evento()

            if trabajo is None:
                time.sleep(
                    POLL_SECONDS
                )
                continue

            procesar(
                trabajo
            )

        except Exception as exc:
            # No registrar str(exc), SQL ni contenido de eventos.
            logger.error(
                (
                    "Error del dispatcher tipo=%s; "
                    "reintento en 5 segundos"
                ),
                type(exc).__name__,
            )

            time.sleep(5)

    logger.info(
        "Audit Dispatcher detenido"
    )


if __name__ == "__main__":
    main()
