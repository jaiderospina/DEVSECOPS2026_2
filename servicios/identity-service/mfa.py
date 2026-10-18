# ============================================================
# IAM SECURE - MFA / TOTP
# ============================================================
# Funciones criptográficas y controles de seguridad para el
# segundo factor mediante aplicaciones Authenticator
# compatibles con TOTP.
#
# SEGURIDAD:
# - El secreto TOTP se genera criptográficamente con PyOTP.
# - El secreto nunca se almacena en texto plano en PostgreSQL.
# - MFA_ENCRYPTION_KEY se obtiene exclusivamente del entorno.
# - Los códigos TOTP no se almacenan ni se registran en logs.
# - La comparación de códigos es realizada por PyOTP.
# - Los códigos aceptados quedan protegidos contra reutilización
#   mediante un contador TOTP persistido de forma atómica.
# ============================================================

import io
import os
from dataclasses import dataclass
from time import time

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from sqlalchemy import text

from database import engine


load_dotenv()


# ============================================================
# CONFIGURACIÓN MFA
# ============================================================

MFA_ENCRYPTION_KEY = os.getenv("MFA_ENCRYPTION_KEY")

if not MFA_ENCRYPTION_KEY:
    raise RuntimeError(
        "La variable MFA_ENCRYPTION_KEY no está configurada"
    )

try:
    _fernet = Fernet(MFA_ENCRYPTION_KEY.encode("utf-8"))
except (ValueError, TypeError) as exc:
    raise RuntimeError(
        "MFA_ENCRYPTION_KEY no tiene un formato Fernet válido"
    ) from exc


# Parámetros TOTP.
# 30 segundos y 6 dígitos corresponden al esquema habitual
# compatible con aplicaciones Authenticator.
TOTP_INTERVAL_SECONDS = 30
TOTP_DIGITS = 6

# Se admite una ventana de un intervalo anterior/posterior para
# tolerar pequeñas diferencias de reloj entre servidor y móvil.
TOTP_VALID_WINDOW = 1

# Nombre que aparecerá en la aplicación Authenticator.
TOTP_ISSUER = "IAM Secure"


# ============================================================
# RESULTADO DE VALIDACIÓN
# ============================================================

@dataclass(frozen=True)
class ResultadoValidacionTOTP:
    valido: bool
    contador: int | None = None


# ============================================================
# GENERACIÓN DEL SECRETO
# ============================================================

def generar_secreto_totp() -> str:
    """
    Genera un secreto Base32 criptográficamente aleatorio para TOTP.

    El valor retornado debe cifrarse antes de persistirse y nunca
    debe escribirse en logs.
    """
    return pyotp.random_base32()


# ============================================================
# CIFRADO DEL SECRETO
# ============================================================

def cifrar_secreto_totp(secreto: str) -> str:
    """
    Cifra el secreto TOTP mediante Fernet antes de almacenarlo.

    PostgreSQL recibe únicamente el texto cifrado.
    """
    if not secreto:
        raise ValueError(
            "El secreto TOTP no puede estar vacío"
        )

    return _fernet.encrypt(
        secreto.encode("utf-8")
    ).decode("utf-8")


def descifrar_secreto_totp(secreto_cifrado: str) -> str:
    """
    Descifra internamente un secreto TOTP.

    El secreto resultante debe permanecer exclusivamente en memoria
    durante la operación que lo requiera.
    """
    if not secreto_cifrado:
        raise ValueError(
            "El secreto TOTP cifrado no puede estar vacío"
        )

    try:
        return _fernet.decrypt(
            secreto_cifrado.encode("utf-8")
        ).decode("utf-8")

    except InvalidToken as exc:
        raise RuntimeError(
            "No fue posible descifrar la configuración MFA"
        ) from exc


# ============================================================
# URI DE APROVISIONAMIENTO
# ============================================================

def generar_uri_aprovisionamiento(
    secreto: str,
    identificador_usuario: str,
) -> str:
    """
    Genera internamente la URI otpauth utilizada durante el
    enrolamiento con una aplicación Authenticator.

    IMPORTANTE:
    La URI contiene el secreto TOTP. Por ello no debe registrarse
    en logs ni almacenarse en PostgreSQL.
    """
    if not secreto:
        raise ValueError(
            "El secreto TOTP no puede estar vacío"
        )

    if not identificador_usuario:
        raise ValueError(
            "El identificador del usuario no puede estar vacío"
        )

    totp = pyotp.TOTP(
        secreto,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL_SECONDS,
    )

    return totp.provisioning_uri(
        name=identificador_usuario,
        issuer_name=TOTP_ISSUER,
    )


# ============================================================
# GENERACIÓN DEL QR DE ENROLAMIENTO
# ============================================================

def generar_qr_aprovisionamiento_png(
    secreto: str,
    identificador_usuario: str,
) -> bytes:
    """
    Genera en memoria un código QR PNG para enrolar el segundo
    factor en una aplicación Authenticator compatible con TOTP.

    SEGURIDAD:
    - La URI otpauth se construye únicamente en memoria.
    - El secreto TOTP no se escribe en disco.
    - No se crean archivos temporales.
    - Esta función retorna únicamente los bytes de la imagen PNG.
    - El endpoint que utilice esta función debe entregar el QR
      únicamente al usuario autenticado que está realizando su
      propio enrolamiento.
    - Ni la URI, ni el secreto, ni los bytes del QR deben enviarse
      al sistema de auditoría o a logs.
    """
    if not secreto:
        raise ValueError(
            "El secreto TOTP no puede estar vacío"
        )

    if not identificador_usuario:
        raise ValueError(
            "El identificador del usuario no puede estar vacío"
        )

    # La URI contiene el secreto TOTP y por ello permanece
    # exclusivamente en memoria durante la creación del QR.
    uri_aprovisionamiento = generar_uri_aprovisionamiento(
        secreto=secreto,
        identificador_usuario=identificador_usuario,
    )

    # El QR se construye completamente en memoria.
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(uri_aprovisionamiento)
    qr.make(fit=True)

    imagen_qr = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer_png = io.BytesIO()

    try:
        imagen_qr.save(
            buffer_png,
            format="PNG",
        )
        return buffer_png.getvalue()
    finally:
        buffer_png.close()


# ============================================================
# VALIDACIÓN TOTP + IDENTIFICACIÓN DEL CONTADOR
# ============================================================

def validar_codigo_totp(
    secreto: str,
    codigo: str,
) -> ResultadoValidacionTOTP:
    """
    Valida un código TOTP y determina exactamente qué contador
    temporal produjo la coincidencia.

    Esta función solamente realiza la validación criptográfica.
    NO modifica PostgreSQL.

    Si el código resulta válido, el contador retornado debe ser
    consumido posteriormente mediante consumir_contador_totp()
    antes de considerar finalizada la autenticación MFA.
    """
    if not secreto or not codigo:
        return ResultadoValidacionTOTP(
            valido=False
        )

    codigo_normalizado = str(codigo).strip()

    if (
        len(codigo_normalizado) != TOTP_DIGITS
        or not codigo_normalizado.isdigit()
    ):
        return ResultadoValidacionTOTP(
            valido=False
        )

    totp = pyotp.TOTP(
        secreto,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL_SECONDS,
    )

    contador_actual = (
        int(time()) // TOTP_INTERVAL_SECONDS
    )

    # Se comprueba explícitamente cada contador permitido en lugar
    # de limitarnos a totp.verify(). Así conocemos el contador que
    # produjo la coincidencia y podemos implementar anti-replay.
    for desplazamiento in range(
        -TOTP_VALID_WINDOW,
        TOTP_VALID_WINDOW + 1,
    ):
        contador = contador_actual + desplazamiento

        if contador < 0:
            continue

        codigo_esperado = totp.at(
            contador * TOTP_INTERVAL_SECONDS
        )

        if pyotp.utils.strings_equal(
            codigo_esperado,
            codigo_normalizado,
        ):
            return ResultadoValidacionTOTP(
                valido=True,
                contador=contador,
            )

    return ResultadoValidacionTOTP(
        valido=False
    )


# ============================================================
# ANTI-REPLAY TOTP
# ============================================================

def consumir_contador_totp(
    usuario_id: int,
    contador: int,
) -> bool:
    """
    Consume de forma atómica un contador TOTP previamente validado.

    SEGURIDAD:
    Un mismo contador no puede aceptarse nuevamente para el mismo
    usuario. La decisión se realiza directamente en PostgreSQL
    mediante un UPDATE condicional.

    Esto evita una condición de carrera en la que dos solicitudes
    concurrentes intenten utilizar el mismo código TOTP.

    Retorna:
        True:
            El contador era nuevo y quedó registrado.

        False:
            El MFA no está activo, el usuario no posee
            configuración MFA o el contador ya había sido
            utilizado/anteriormente aceptado.

    IMPORTANTE:
    Esta función NO recibe ni almacena el código TOTP ni el secreto.
    """
    if (
        not isinstance(usuario_id, int)
        or isinstance(usuario_id, bool)
        or usuario_id <= 0
    ):
        return False

    if (
        not isinstance(contador, int)
        or isinstance(contador, bool)
        or contador < 0
    ):
        return False

    actualizar_contador = text("""
        UPDATE mfa_totp
        SET
            ultimo_contador_validado = :contador,
            fecha_modificacion = NOW()
        WHERE usuario_id = :usuario_id
          AND activo = TRUE
          AND (
              ultimo_contador_validado IS NULL
              OR ultimo_contador_validado < :contador
          )
    """)

    # engine.begin() garantiza que el UPDATE se confirme como una
    # única transacción. La condición se evalúa en PostgreSQL,
    # evitando separar "consultar" y "actualizar" en dos pasos.
    with engine.begin() as conexion:
        resultado = conexion.execute(
            actualizar_contador,
            {
                "usuario_id": usuario_id,
                "contador": contador,
            },
        )

    # Exactamente una fila modificada significa que el contador
    # fue consumido por esta solicitud.
    return resultado.rowcount == 1