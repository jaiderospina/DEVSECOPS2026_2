import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr


# ============================================================
# CONFIGURACIÓN SEGURA DEL SERVICIO DE CORREO
# ============================================================
# Las credenciales SMTP se obtienen exclusivamente mediante
# variables de entorno. No deben escribirse en código fuente,
# Dockerfile, repositorio, logs ni respuestas de API.
# ============================================================

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT_RAW = os.getenv("SMTP_PORT", "587")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USER


# ============================================================
# VALIDACIÓN DE CONFIGURACIÓN
# ============================================================

def validar_configuracion_correo() -> None:
    """
    Valida la configuración necesaria para el envío SMTP.

    SEGURIDAD:
    - no imprime valores de configuración;
    - no expone usuario ni contraseña SMTP;
    - valida el puerto antes de abrir una conexión.
    """

    faltantes = []

    if not SMTP_HOST or not SMTP_HOST.strip():
        faltantes.append("SMTP_HOST")

    if not SMTP_USER or not SMTP_USER.strip():
        faltantes.append("SMTP_USER")

    if not SMTP_PASSWORD or not SMTP_PASSWORD.strip():
        faltantes.append("SMTP_PASSWORD")

    if not SMTP_FROM or not SMTP_FROM.strip():
        faltantes.append("SMTP_FROM")

    if faltantes:
        raise RuntimeError(
            "Configuración SMTP incompleta"
        )

    try:
        puerto = int(SMTP_PORT_RAW)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "SMTP_PORT debe ser un número entero válido"
        ) from exc

    if not 1 <= puerto <= 65535:
        raise RuntimeError(
            "SMTP_PORT debe estar entre 1 y 65535"
        )


def _obtener_puerto_smtp() -> int:
    """Devuelve el puerto SMTP después de validar configuración."""
    validar_configuracion_correo()
    return int(SMTP_PORT_RAW)


def _validar_direccion_correo(direccion: str, campo: str) -> str:
    """
    Realiza una validación defensiva del encabezado de correo.

    Los endpoints principales ya utilizan EmailStr para los correos
    almacenados. Esta comprobación adicional evita encabezados vacíos
    o con saltos de línea si la función se reutiliza en otro contexto.
    """

    if not isinstance(direccion, str):
        raise ValueError(f"{campo} no es válido")

    direccion = direccion.strip()

    if not direccion or "\r" in direccion or "\n" in direccion:
        raise ValueError(f"{campo} no es válido")

    _, email_parseado = parseaddr(direccion)

    if (
        not email_parseado
        or email_parseado != direccion
        or "@" not in email_parseado
    ):
        raise ValueError(f"{campo} no es válido")

    return direccion


# ============================================================
# ENVÍO DE CONTRASEÑA TEMPORAL
# ============================================================

def enviar_password_temporal(
    destinatario: str,
    nombre_usuario: str,
    password_temporal: str
) -> None:
    """
    Envía la contraseña temporal generada por Identity Service.

    SEGURIDAD:
    - la contraseña no se imprime ni registra;
    - no se persiste en este módulo;
    - se utiliza únicamente para construir el mensaje;
    - PostgreSQL conserva únicamente el hash Argon2;
    - la conexión SMTP utiliza STARTTLS antes del login.
    """

    puerto = _obtener_puerto_smtp()

    destinatario_seguro = _validar_direccion_correo(
        destinatario,
        "Destinatario"
    )

    remitente_seguro = _validar_direccion_correo(
        SMTP_FROM,
        "Remitente"
    )

    # Evita introducir saltos de línea o contenido inesperado en
    # el saludo del mensaje. La contraseña no se modifica.
    nombre_seguro = (
        str(nombre_usuario)
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )

    if not nombre_seguro:
        nombre_seguro = "usuario"

    if not isinstance(password_temporal, str) or not password_temporal:
        raise ValueError(
            "No fue posible construir el mensaje temporal"
        )

    mensaje = EmailMessage()
    mensaje["Subject"] = "Acceso temporal - IAM Secure"
    mensaje["From"] = formataddr(("IAM Secure", remitente_seguro))
    mensaje["To"] = destinatario_seguro

    mensaje.set_content(
        f"""Hola {nombre_seguro},

Se ha generado una contraseña temporal para acceder a IAM Secure.

Contraseña temporal:
{password_temporal}

Por seguridad, al iniciar sesión deberás cambiar esta contraseña antes de acceder a la plataforma correspondiente.

La contraseña temporal tiene una vigencia limitada. Si ya expiró, solicita un nuevo restablecimiento de acceso.

Si no esperabas este mensaje, comunícate con el administrador del sistema.

IAM Secure
"""
    )

    # ========================================================
    # CONEXIÓN SMTP SEGURA
    # ========================================================
    # Se crea un contexto TLS del sistema y STARTTLS se ejecuta
    # antes de transmitir las credenciales SMTP.
    # ========================================================

    contexto_tls = ssl.create_default_context()

    with smtplib.SMTP(
        SMTP_HOST.strip(),
        puerto,
        timeout=15
    ) as servidor:

        servidor.ehlo()

        servidor.starttls(
            context=contexto_tls
        )

        servidor.ehlo()

        servidor.login(
            SMTP_USER.strip(),
            SMTP_PASSWORD
        )

        servidor.send_message(
            mensaje
        )
