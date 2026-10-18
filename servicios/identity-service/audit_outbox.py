# ============================================================
# IAM SECURE - AUDIT OUTBOX
# ============================================================
#
# Persiste eventos de auditoría sanitizados antes de intentar
# enviarlos al Audit Service.
#
# SEGURIDAD:
# - nunca registra el contenido completo del evento;
# - nunca registra credenciales ni secretos;
# - evento_uuid permite idempotencia;
# - con una conexión transaccional, fallar auditoría revierte
#   también la operación principal; el modo histórico sigue best-effort.
# ============================================================

from contextlib import nullcontext

import json
import logging

from sqlalchemy import text

from database import engine


logger = logging.getLogger(
    "iam.audit.outbox"
)


MAX_DETALLE_BYTES = 16 * 1024


def encolar_evento_auditoria(
    evento: dict,
    *,
    conexion=None,
) -> bool:
    """
    Guarda un evento sanitizado en auditoria_outbox.

    Con conexion, participa en la transacción del llamador y propaga
    errores para que se revierta también la operación de seguridad.
    Sin conexion conserva el contrato best-effort de los otros eventos.

    Retorna:
        True  -> evento disponible en la Outbox.
        False -> no fue posible garantizar persistencia.
    """

    if not isinstance(evento, dict):
        logger.error(
            "Evento de auditoría inválido para Outbox"
        )
        if conexion is not None:
            raise ValueError("No se pudo asegurar el evento de auditoría")
        return False

    detalle = evento.get(
        "detalle",
        {},
    )

    if not isinstance(detalle, dict):
        logger.error(
            "Detalle de auditoría inválido para Outbox"
        )
        if conexion is not None:
            raise ValueError("No se pudo asegurar el evento de auditoría")
        return False

    try:
        detalle_json = json.dumps(
            detalle,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    except Exception as exc:
        logger.error(
            (
                "No fue posible serializar detalle "
                "de auditoría tipo=%s"
            ),
            type(exc).__name__,
        )
        if conexion is not None:
            raise ValueError("No se pudo asegurar el evento de auditoría")
        return False

    if (
        len(
            detalle_json.encode("utf-8")
        )
        > MAX_DETALLE_BYTES
    ):
        logger.warning(
            "Detalle de auditoría excede límite permitido"
        )
        if conexion is not None:
            raise ValueError("No se pudo asegurar el evento de auditoría")
        return False

    insertar = text(
        """
        INSERT INTO auditoria_outbox (
            evento_uuid,
            fecha_evento,
            servicio,
            evento,
            resultado,
            actor_usuario_id,
            objetivo_usuario_id,
            compania_id,
            detalle
        )
        VALUES (
            CAST(:evento_uuid AS UUID),
            :fecha_evento,
            :servicio,
            :evento,
            :resultado,
            :actor_usuario_id,
            :objetivo_usuario_id,
            :compania_id,
            CAST(:detalle AS JSONB)
        )
        ON CONFLICT (evento_uuid)
        DO NOTHING
        RETURNING id
        """
    )

    consultar = text(
        """
        SELECT id
        FROM auditoria_outbox
        WHERE evento_uuid =
            CAST(:evento_uuid AS UUID)
        """
    )

    try:
        contexto = engine.begin() if conexion is None else nullcontext(conexion)
        with contexto as transaccion:

            fila = transaccion.execute(
                insertar,
                {
                    "evento_uuid":
                        evento["evento_uuid"],

                    "fecha_evento":
                        evento["fecha_evento"],

                    "servicio":
                        evento["servicio"],

                    "evento":
                        evento["evento"],

                    "resultado":
                        evento["resultado"],

                    "actor_usuario_id":
                        evento.get(
                            "actor_usuario_id"
                        ),

                    "objetivo_usuario_id":
                        evento.get(
                            "objetivo_usuario_id"
                        ),

                    "compania_id":
                        evento.get(
                            "compania_id"
                        ),

                    "detalle":
                        detalle_json,
                },
            ).mappings().first()

            if fila is not None:
                return True

            # ------------------------------------------------
            # IDEMPOTENCIA
            # ------------------------------------------------
            # Si ya existía el mismo UUID, consideramos que el
            # evento está asegurado en la Outbox.
            # ------------------------------------------------

            existente = transaccion.execute(
                consultar,
                {
                    "evento_uuid":
                        evento["evento_uuid"]
                },
            ).mappings().first()

            if existente is None and conexion is not None:
                raise RuntimeError("No se pudo asegurar el evento de auditoría")
            return existente is not None

    except Exception as exc:
        # No registrar str(exc), SQL, evento ni parámetros.
        logger.error(
            (
                "No fue posible persistir auditoría "
                "en Outbox tipo=%s"
            ),
            type(exc).__name__,
        )

        if conexion is not None:
            raise
        return False
