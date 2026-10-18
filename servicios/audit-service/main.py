from __future__ import annotations

import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from sqlalchemy import text

from database import engine, verificar_conexion
from http_headers import ApiSecurityHeadersMiddleware
from seguridad import sanitizar_detalle


# ============================================================
# IAM SECURE - AUDIT SERVICE
# ============================================================
#
# RESPONSABILIDADES:
# - recibir eventos estructurados desde servicios autorizados;
# - aplicar sanitización defensiva adicional;
# - persistir eventos append-only;
# - soportar reintentos idempotentes mediante evento_uuid.
#
# SEGURIDAD:
# - no acepta modificación ni eliminación de eventos;
# - no registra cuerpos de solicitudes;
# - no registra tokens internos;
# - no debe almacenar contraseñas, hashes, JWT/JTI, TOTP,
#   secretos MFA, QR ni credenciales de infraestructura.
# ============================================================

load_dotenv()


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

logger = logging.getLogger(
    "iam-secure-audit-service"
)


# ============================================================
# AUTENTICACIÓN ENTRE SERVICIOS
# ============================================================
#
# Identity Service y otros productores utilizarán un secreto
# independiente exclusivamente para enviar eventos de auditoría.
#
# El valor real existe únicamente en .env / entorno Docker.
# ============================================================

AUDIT_INTERNAL_TOKEN = os.getenv(
    "AUDIT_INTERNAL_TOKEN"
)

if (
    AUDIT_INTERNAL_TOKEN is None
    or len(AUDIT_INTERNAL_TOKEN.strip()) < 32
):
    raise RuntimeError(
        "AUDIT_INTERNAL_TOKEN no está configurado correctamente"
    )

AUDIT_INTERNAL_TOKEN = (
    AUDIT_INTERNAL_TOKEN.strip()
)


# ============================================================
# LÍMITE DEL DETALLE
# ============================================================
#
# Evita utilizar la auditoría como almacenamiento arbitrario
# de objetos excesivamente grandes.
# ============================================================

MAX_DETALLE_BYTES = 16 * 1024


# ============================================================
# MODELO DE ENTRADA
# ============================================================

class EventoAuditoriaEntrada(BaseModel):
    """
    Evento recibido desde un servicio interno autorizado.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    evento_uuid: UUID

    fecha_evento: datetime

    servicio: str = Field(
        min_length=1,
        max_length=100,
    )

    evento: str = Field(
        min_length=1,
        max_length=100,
    )

    resultado: str = Field(
        min_length=1,
        max_length=50,
    )

    actor_usuario_id: int | None = Field(
        default=None,
        gt=0,
    )

    objetivo_usuario_id: int | None = Field(
        default=None,
        gt=0,
    )

    compania_id: int | None = Field(
        default=None,
        gt=0,
    )

    detalle: dict[str, Any] = Field(
        default_factory=dict
    )

    @field_validator(
        "servicio",
        "evento",
        "resultado",
    )
    @classmethod
    def normalizar_texto(
        cls,
        valor: str,
    ) -> str:
        valor = valor.strip()

        if not valor:
            raise ValueError(
                "El valor no puede estar vacío"
            )

        return valor

    @field_validator("fecha_evento")
    @classmethod
    def validar_zona_horaria(
        cls,
        valor: datetime,
    ) -> datetime:
        """
        Los eventos deben incluir zona horaria explícita para
        evitar timestamps ambiguos.
        """
        if (
            valor.tzinfo is None
            or valor.utcoffset() is None
        ):
            raise ValueError(
                "fecha_evento debe incluir zona horaria"
            )

        return valor


# ============================================================
# MODELO DE RESPUESTA
# ============================================================

class EventoAuditoriaRespuesta(BaseModel):
    id: int
    evento_uuid: UUID
    creado: bool


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="IAM Secure Audit Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Cabecera de seguridad aplicada también a errores y rutas auxiliares.
app.add_middleware(ApiSecurityHeadersMiddleware)


# ============================================================
# RESPUESTAS SEGURAS DE VALIDACIÓN
# ============================================================
#
# FastAPI/Pydantic puede incluir el valor recibido dentro del
# detalle de un error 422.
#
# Como el cuerpo podría contener datos que debieron ser
# sanitizados, devolvemos una respuesta genérica.
# ============================================================

@app.exception_handler(
    RequestValidationError
)
async def manejar_error_validacion(
    _request,
    _exc,
):
    return JSONResponse(
        status_code=422,
        content={
            "detail":
                "Solicitud de auditoría inválida"
        },
    )


# ============================================================
# AUTORIZACIÓN INTERNA
# ============================================================

def validar_token_interno(
    x_iam_audit_token: str | None = Header(
        default=None,
        alias="X-IAM-Audit-Token",
    ),
) -> None:
    """
    Compara el token en tiempo constante.

    El token nunca se devuelve ni se registra.
    """

    if not x_iam_audit_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Servicio no autorizado",
        )

    token_recibido = (
        x_iam_audit_token.strip()
    )

    if not hmac.compare_digest(
        token_recibido,
        AUDIT_INTERNAL_TOKEN,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Servicio no autorizado",
        )


# ============================================================
# HEALTHCHECK
# ============================================================

@app.get("/health")
def health():
    """
    Comprueba que Audit Service y PostgreSQL están disponibles.

    No expone configuración interna.
    """

    try:
        verificar_conexion()

    except Exception as exc:
        logger.warning(
            "Healthcheck PostgreSQL falló tipo=%s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio temporalmente no disponible",
        ) from None

    return {
        "status": "ok"
    }


# ============================================================
# CREAR EVENTO DE AUDITORÍA
# ============================================================

@app.post(
    "/eventos",
    response_model=EventoAuditoriaRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_evento(
    evento_entrada: EventoAuditoriaEntrada,
    response: Response,
    _autorizado: None = Depends(
        validar_token_interno
    ),
):
    """
    Persiste un evento de auditoría de forma idempotente.

    Si el mismo evento_uuid es recibido nuevamente, no se crea
    una segunda fila y se devuelve el identificador existente.
    """

    # --------------------------------------------------------
    # SEGUNDA SANITIZACIÓN
    # --------------------------------------------------------
    #
    # No se confía exclusivamente en el servicio productor.
    # --------------------------------------------------------

    detalle_seguro = sanitizar_detalle(
        evento_entrada.detalle
    )

    detalle_json = json.dumps(
        detalle_seguro,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    if (
        len(
            detalle_json.encode("utf-8")
        )
        > MAX_DETALLE_BYTES
    ):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Detalle de auditoría demasiado grande",
        )

    # --------------------------------------------------------
    # NORMALIZACIÓN
    # --------------------------------------------------------

    servicio = (
        evento_entrada.servicio
        .strip()
        .lower()
    )

    nombre_evento = (
        evento_entrada.evento
        .strip()
        .upper()
    )

    resultado = (
        evento_entrada.resultado
        .strip()
        .upper()
    )

    # --------------------------------------------------------
    # INSERT IDEMPOTENTE
    # --------------------------------------------------------

    insertar = text(
        """
        INSERT INTO auditoria_eventos (
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

    consultar_existente = text(
        """
        SELECT id
        FROM auditoria_eventos
        WHERE evento_uuid =
            CAST(:evento_uuid AS UUID)
        """
    )

    try:
        with engine.begin() as conexion:
            fila = conexion.execute(
                insertar,
                {
                    "evento_uuid":
                        str(
                            evento_entrada.evento_uuid
                        ),

                    "fecha_evento":
                        evento_entrada.fecha_evento,

                    "servicio":
                        servicio,

                    "evento":
                        nombre_evento,

                    "resultado":
                        resultado,

                    "actor_usuario_id":
                        evento_entrada.actor_usuario_id,

                    "objetivo_usuario_id":
                        evento_entrada.objetivo_usuario_id,

                    "compania_id":
                        evento_entrada.compania_id,

                    "detalle":
                        detalle_json,
                },
            ).mappings().first()

            creado = fila is not None

            if creado:
                evento_id = fila["id"]

            else:
                existente = conexion.execute(
                    consultar_existente,
                    {
                        "evento_uuid":
                            str(
                                evento_entrada.evento_uuid
                            )
                    },
                ).mappings().first()

                if existente is None:
                    raise RuntimeError(
                        "No fue posible resolver el evento idempotente"
                    )

                evento_id = existente["id"]

    except HTTPException:
        raise

    except Exception as exc:
        # ----------------------------------------------------
        # SEGURIDAD
        # ----------------------------------------------------
        # No registramos str(exc), SQL ni parámetros porque
        # podrían revelar información interna.
        # ----------------------------------------------------

        logger.error(
            "Error persistiendo auditoría tipo=%s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar el evento",
        ) from None

    # Un reintento idempotente no crea una fila nueva.
    if not creado:
        response.status_code = (
            status.HTTP_200_OK
        )

    logger.info(
        (
            "Evento de auditoría procesado "
            "id=%s creado=%s evento=%s"
        ),
        evento_id,
        creado,
        nombre_evento,
    )

    return EventoAuditoriaRespuesta(
        id=evento_id,
        evento_uuid=
            evento_entrada.evento_uuid,
        creado=creado,
    )