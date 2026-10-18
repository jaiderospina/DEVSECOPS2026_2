# ============================================================

"""
Módulo de auditoría del Identity Service.

Este módulo genera eventos estructurados de seguridad y administración.

IMPORTANTE:
- No almacena contraseñas.
- No almacena hashes.
- No almacena JWT.
- No almacena JTI.
- No almacena secretos.
- Sanitiza estructuras anidadas antes de enviarlas al logger y a la Outbox.
- No se comunica directamente con Audit Service.

En la arquitectura actual, Identity Service registra el evento local y
persiste una copia sanitizada en auditoria_outbox. Audit Dispatcher realiza
posteriormente la entrega asíncrona a Audit Service.
"""

import json
import logging
import sys
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from audit_outbox import encolar_evento_auditoria


# ============================================================
# LOGGER EXCLUSIVO DE AUDITORÍA
# ============================================================
# Uvicorn configura sus propios loggers, pero este módulo utiliza
# un logger independiente para los eventos de auditoría.
#
# Los eventos se escriben como JSON estructurado en stdout para
# que Docker pueda capturarlos y posteriormente enviarlos a un
# sistema centralizado de observabilidad o al futuro Audit Service.
#
# No utilizamos FileHandler porque el contenedor debe permanecer
# stateless.
# ============================================================

logger_auditoria = logging.getLogger("iam.audit")
logger_auditoria.setLevel(logging.INFO)

# Evita que el mismo evento sea enviado también al logger raíz.
logger_auditoria.propagate = False


# ============================================================
# HANDLER DE AUDITORÍA
# ============================================================
# Se agrega únicamente si todavía no existe uno configurado.
# Esto evita registros duplicados durante imports repetidos,
# recargas del entorno de desarrollo o pruebas.
# ============================================================

if not logger_auditoria.handlers:
    handler_auditoria = logging.StreamHandler(
        sys.stdout
    )

    handler_auditoria.setLevel(
        logging.INFO
    )

    # registrar_evento() ya genera JSON.
    # No agregamos prefijos que alteren el formato estructurado.
    handler_auditoria.setFormatter(
        logging.Formatter("%(message)s")
    )

    logger_auditoria.addHandler(
        handler_auditoria
    )


# ============================================================
# EVENTOS SOPORTADOS
# ============================================================
# Centralizar los nombres evita utilizar cadenas diferentes para
# representar el mismo evento en distintos módulos.
# ============================================================

LOGIN_EXITOSO = "LOGIN_EXITOSO"
LOGIN_FALLIDO = "LOGIN_FALLIDO"

CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"
CUENTA_DESBLOQUEADA = "CUENTA_DESBLOQUEADA"

LOGOUT = "LOGOUT"

SESION_REVOCADA = "SESION_REVOCADA"
SESIONES_USUARIO_REVOCADAS = "SESIONES_USUARIO_REVOCADAS"
SESION_EXPIRADA_INACTIVIDAD = "SESION_EXPIRADA_INACTIVIDAD"
SESIONES_EXPIRADAS_ELIMINADAS = "SESIONES_EXPIRADAS_ELIMINADAS"

PASSWORD_CAMBIADA = "PASSWORD_CAMBIADA"
PASSWORD_RESET_ADMIN = "PASSWORD_RESET_ADMIN"
PASSWORD_RECUPERADA = "PASSWORD_RECUPERADA"

# ============================================================
# EVENTOS DE AUTENTICACIÓN MULTIFACTOR (MFA/TOTP)
# ============================================================
# Estos eventos permiten auditar el ciclo de vida del segundo
# factor sin almacenar información que permita reconstruirlo.
#
# SEGURIDAD:
# - nunca registrar el secreto TOTP;
# - nunca registrar códigos OTP/TOTP;
# - nunca registrar la URI otpauth;
# - nunca registrar el contenido del código QR.
# ============================================================

MFA_ENROLAMIENTO_INICIADO = "MFA_ENROLAMIENTO_INICIADO"
MFA_ACTIVADO = "MFA_ACTIVADO"
MFA_LOGIN_EXITOSO = "MFA_LOGIN_EXITOSO"
MFA_LOGIN_FALLIDO = "MFA_LOGIN_FALLIDO"
MFA_DESACTIVADO = "MFA_DESACTIVADO"
MFA_RESTABLECIDO_ADMIN = "MFA_RESTABLECIDO_ADMIN"

USUARIO_CREADO = "USUARIO_CREADO"
USUARIO_MODIFICADO = "USUARIO_MODIFICADO"
USUARIO_ESTADO_MODIFICADO = "USUARIO_ESTADO_MODIFICADO"
USUARIO_ROL_MODIFICADO = "USUARIO_ROL_MODIFICADO"

COMPANIA_CREADA = "COMPANIA_CREADA"
COMPANIA_MODIFICADA = "COMPANIA_MODIFICADA"
COMPANIA_ESTADO_MODIFICADO = "COMPANIA_ESTADO_MODIFICADO"
COMPANIA_ASIGNADA = "COMPANIA_ASIGNADA"
COMPANIA_REASIGNADA = "COMPANIA_REASIGNADA"
COMPANIA_DESASIGNADA = "COMPANIA_DESASIGNADA"


# ============================================================
# CAMPOS SENSIBLES
# ============================================================
# Defensa en profundidad frente al registro accidental de
# credenciales, tokens, secretos o material criptográfico.
#
# Las claves se normalizan mediante:
#
#     strip().lower()
#
# antes de realizar la comparación.
#
# La aplicación no debe depender exclusivamente de este mecanismo:
# los endpoints tampoco deben enviar secretos a registrar_evento().
# Esta sanitización constituye una segunda capa de protección.
# ============================================================

CAMPOS_SENSIBLES = {
    # --------------------------------------------------------
    # Contraseñas
    # --------------------------------------------------------
    "password",
    "password_hash",
    "password_temporal",
    "password_nuevo",
    "password_actual",
    "new_password",
    "current_password",
    "temporary_password",
    "contrasena",
    "contraseña",

    # --------------------------------------------------------
    # Tokens y autenticación
    # --------------------------------------------------------
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "jwt",
    "jti",

    # --------------------------------------------------------
    # Secretos y claves
    # --------------------------------------------------------
    "secret",
    "jwt_secret",
    "client_secret",
    "api_key",
    "apikey",
    "private_key",
    "session_token",
    "cookie",
    "set_cookie",
    "credential",
    "credentials",
    "credencial",
    "credenciales",

    # --------------------------------------------------------
    # Autenticación multifactor (MFA / TOTP)
    # --------------------------------------------------------
    # Estos nombres se bloquean explícitamente para impedir que
    # secretos, códigos temporales o material de enrolamiento
    # puedan llegar accidentalmente a los logs de auditoría.
    # --------------------------------------------------------
    "totp",
    "otp",
    "codigo_totp",
    "codigo_otp",
    "mfa_code",
    "mfa_codigo",
    "secreto_totp",
    "totp_secret",
    "mfa_secret",
    "otpauth",
    "otpauth_uri",
    "qr",
    "qr_code",
    "qr_data",

    # --------------------------------------------------------
    # Infraestructura
    # --------------------------------------------------------
    "smtp_password",
    "db_password",
    "postgres_password",
}


# ============================================================
# INDICADORES DE NOMBRES SENSIBLES
# ============================================================
# Además de las coincidencias exactas anteriores, protegemos
# variantes razonables como:
#
#   usuario_password
#   password_confirmacion
#   oauth_access_token
#   servicio_client_secret
#
# No utilizamos simplemente "secret" o "token" como búsqueda
# arbitraria sobre valores. La comprobación se realiza únicamente
# sobre el NOMBRE de la clave.
# ============================================================

PATRONES_CLAVE_SENSIBLE = (
    "password",
    "passwd",
    "contrasena",
    "contraseña",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "jwt_secret",
    "api_key",
    "apikey",
    "private_key",
    "session_token",
    "cookie",
    "credential",
    "credencial",

    # MFA / TOTP
    "totp",
    "otp",
    "mfa_code",
    "mfa_codigo",
    "otpauth",
    "qr_code",
    "qr_data",
)


# ============================================================
# NORMALIZACIÓN DE CLAVES
# ============================================================

def _normalizar_clave(clave: Any) -> str:
    """
    Convierte una clave a una representación normalizada para
    realizar las comprobaciones de seguridad.

    La función no modifica el nombre original almacenado en el
    evento; solamente produce una versión para comparación.
    """

    return str(clave).strip().lower()


# ============================================================
# DETECCIÓN DE CLAVES SENSIBLES
# ============================================================

def _es_clave_sensible(clave: Any) -> bool:
    """
    Determina si el nombre de una clave puede contener un secreto.

    Primero se evalúan coincidencias exactas y posteriormente
    patrones asociados a credenciales o material sensible.
    """

    clave_normalizada = _normalizar_clave(
        clave
    )

    # Coincidencia exacta.
    if clave_normalizada in CAMPOS_SENSIBLES:
        return True

    # Defensa adicional frente a variantes de nombres.
    return any(
        patron in clave_normalizada
        for patron in PATRONES_CLAVE_SENSIBLE
    )


# ============================================================
# SANITIZACIÓN RECURSIVA
# ============================================================

def _sanitizar_valor(valor: Any) -> Any:
    """
    Sanitiza estructuras anidadas antes de escribirlas en logs.

    Reglas principales:

    - Las claves sensibles se sustituyen por [REDACTED].
    - Los diccionarios se recorren recursivamente.
    - Las listas, tuplas y conjuntos se sanitizan elemento a
      elemento.
    - Los tipos escalares seguros se conservan.
    - datetime y date se serializan mediante ISO 8601.
    - Objetos desconocidos no se convierten directamente a str(),
      porque su representación podría contener información
      sensible.
    """

    # --------------------------------------------------------
    # DICCIONARIOS
    # --------------------------------------------------------

    if isinstance(valor, dict):
        resultado = {}

        for clave, contenido in valor.items():
            clave_texto = str(clave)

            if _es_clave_sensible(
                clave_texto
            ):
                resultado[clave_texto] = (
                    "[REDACTED]"
                )

            else:
                resultado[clave_texto] = (
                    _sanitizar_valor(
                        contenido
                    )
                )

        return resultado

    # --------------------------------------------------------
    # COLECCIONES
    # --------------------------------------------------------

    if isinstance(
        valor,
        (list, tuple, set)
    ):
        return [
            _sanitizar_valor(elemento)
            for elemento in valor
        ]

    # --------------------------------------------------------
    # FECHAS
    # --------------------------------------------------------
    # Son frecuentes en eventos de seguridad y pueden
    # serializarse de forma segura mediante ISO 8601.
    # --------------------------------------------------------

    if isinstance(
        valor,
        (datetime, date)
    ):
        return valor.isoformat()

    # --------------------------------------------------------
    # TIPOS ESCALARES
    # --------------------------------------------------------

    if (
        isinstance(
            valor,
            (str, int, float, bool)
        )
        or valor is None
    ):
        return valor

    # --------------------------------------------------------
    # OBJETOS NO RECONOCIDOS
    # --------------------------------------------------------
    # No usamos str(valor), ya que __str__ o __repr__ de un
    # objeto podría incluir credenciales, cadenas de conexión,
    # tokens u otros datos internos.
    # --------------------------------------------------------

    return "[UNSUPPORTED_TYPE]"


# ============================================================
# REGISTRO DEL EVENTO
# ============================================================

def registrar_evento(
    evento: str,
    *,
    actor_usuario_id: Optional[int] = None,
    objetivo_usuario_id: Optional[int] = None,
    compania_id: Optional[int] = None,
    resultado: str = "EXITO",
    detalle: Optional[dict] = None,
    conexion=None,
) -> None:
    """
    Genera un evento estructurado de auditoría.

    Los identificadores internos permiten correlacionar eventos
    sin registrar credenciales ni tokens.

    El contenido de detalle siempre pasa por el sanitizador antes
    de llegar al logger.
    """

    # --------------------------------------------------------
    # VALIDAR / NORMALIZAR METADATOS DEL EVENTO
    # --------------------------------------------------------
    # Los nombres de evento y resultado no contienen secretos,
    # pero deben permanecer consistentes para facilitar su
    # correlación y análisis posterior.
    # --------------------------------------------------------

    evento_normalizado = str(evento).strip().upper()
    resultado_normalizado = str(resultado).strip().upper()

    if not evento_normalizado:
        evento_normalizado = "EVENTO_NO_ESPECIFICADO"

    if not resultado_normalizado:
        resultado_normalizado = "NO_ESPECIFICADO"

    # --------------------------------------------------------
    # CONSTRUIR EVENTO
    # --------------------------------------------------------
    #
    # El UUID se genera una única vez por llamada y permite
    # correlacionar el registro local con el evento persistido
    # por Audit Service.
    #
    # El detalle se sanitiza ANTES de utilizarse en cualquiera
    # de los dos destinos.
    # --------------------------------------------------------

    evento_uuid = str(
        uuid4()
    )

    fecha_evento = datetime.now(
        timezone.utc
    ).isoformat()

    detalle_seguro = _sanitizar_valor(
        detalle or {}
    )

    # --------------------------------------------------------
    # EVENTO LOCAL
    # --------------------------------------------------------
    #
    # Se conserva el registro JSON en stdout como mecanismo
    # adicional de observabilidad y respaldo operativo.
    # --------------------------------------------------------

    evento_auditoria_local = {
        "timestamp":
            fecha_evento,

        "evento_uuid":
            evento_uuid,

        "servicio":
            "identity-service",

        "evento":
            evento_normalizado,

        "resultado":
            resultado_normalizado,

        "actor_usuario_id":
            actor_usuario_id,

        "objetivo_usuario_id":
            objetivo_usuario_id,

        "compania_id":
            compania_id,

        "detalle":
            detalle_seguro,
    }

    evento_json = json.dumps(
        evento_auditoria_local,
        ensure_ascii=True,
        separators=(",", ":"),
        default=lambda _objeto:
            "[UNSUPPORTED_TYPE]",
    )

    # El outbox transaccional es la evidencia canónica: no emitir un
    # EXITO local antes de conocer el COMMIT del llamador.
    if conexion is None:
        # Keep stdout one ASCII JSON record, including CR/LF and Unicode line
        # separators supplied in user-controlled details. Outbox retains JSON.
        logger_auditoria.info(evento_json.replace("\r", "\\r").replace("\n", "\\n"))

    # --------------------------------------------------------
    # EVENTO REMOTO
    # --------------------------------------------------------
    #
    # Audit Service utiliza fecha_evento como nombre del campo
    # temporal persistido en PostgreSQL.
    #
    # SEGURIDAD / RESILIENCIA:
    # Identity Service no realiza llamadas HTTP a Audit Service.
    # El evento remoto se entrega mediante la Outbox persistente
    # y Audit Dispatcher, manteniendo desacoplada la operación.
    # --------------------------------------------------------

    evento_auditoria_remoto = {
        "evento_uuid":
            evento_uuid,

        "fecha_evento":
            fecha_evento,

        "servicio":
            "identity-service",

        "evento":
            evento_normalizado,

        "resultado":
            resultado_normalizado,

        "actor_usuario_id":
            actor_usuario_id,

        "objetivo_usuario_id":
            objetivo_usuario_id,

        "compania_id":
            compania_id,

        "detalle":
            detalle_seguro,
    }

    # --------------------------------------------------------
    # OUTBOX PERSISTENTE
    # --------------------------------------------------------
    #
    # Identity Service no se comunica directamente con Audit
    # Service. Su responsabilidad termina al persistir el evento
    # sanitizado en la Outbox.
    #
    # Audit Dispatcher realiza posteriormente la entrega,
    # aplicando reintentos, recuperación e idempotencia.
    # --------------------------------------------------------

    if conexion is None:
        encolar_evento_auditoria(evento_auditoria_remoto)
    else:
        # La excepción aborta el reset y la revocación en la misma conexión.
        encolar_evento_auditoria(evento_auditoria_remoto, conexion=conexion)
