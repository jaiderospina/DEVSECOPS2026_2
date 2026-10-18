from __future__ import annotations

from datetime import date, datetime
from typing import Any


# ============================================================
# IAM SECURE - AUDIT SERVICE
# SANITIZACIÓN DEFENSIVA
# ============================================================
#
# Audit Service vuelve a sanitizar todo campo "detalle" recibido.
#
# Esto constituye una segunda barrera de seguridad aunque el
# servicio productor ya haya aplicado su propia sanitización.
# ============================================================


CAMPOS_SENSIBLES = {
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

    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "jwt",
    "jti",

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

    "smtp_password",
    "db_password",
    "postgres_password",
}


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
    "totp",
    "otp",
    "mfa_code",
    "mfa_codigo",
    "otpauth",
    "qr_code",
    "qr_data",
)


MAX_PROFUNDIDAD = 8


def _normalizar_clave(clave: Any) -> str:
    return str(clave).strip().lower()


def _es_clave_sensible(clave: Any) -> bool:
    clave_normalizada = _normalizar_clave(
        clave
    )

    if clave_normalizada in CAMPOS_SENSIBLES:
        return True

    return any(
        patron in clave_normalizada
        for patron in PATRONES_CLAVE_SENSIBLE
    )


def sanitizar_valor(
    valor: Any,
    *,
    profundidad: int = 0,
) -> Any:
    """
    Sanitiza recursivamente estructuras recibidas.

    SEGURIDAD:
    - redacta claves sensibles;
    - limita profundidad;
    - no convierte objetos desconocidos mediante str();
    - normaliza fechas de forma segura.
    """

    if profundidad > MAX_PROFUNDIDAD:
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(valor, dict):
        resultado = {}

        for clave, contenido in valor.items():
            clave_texto = str(clave)

            if _es_clave_sensible(clave_texto):
                resultado[clave_texto] = "[REDACTED]"
            else:
                resultado[clave_texto] = sanitizar_valor(
                    contenido,
                    profundidad=profundidad + 1,
                )

        return resultado

    if isinstance(
        valor,
        (list, tuple, set),
    ):
        return [
            sanitizar_valor(
                elemento,
                profundidad=profundidad + 1,
            )
            for elemento in valor
        ]

    if isinstance(
        valor,
        (datetime, date),
    ):
        return valor.isoformat()

    if (
        isinstance(
            valor,
            (str, int, float, bool),
        )
        or valor is None
    ):
        return valor

    return "[UNSUPPORTED_TYPE]"


def sanitizar_detalle(
    detalle: dict[str, Any],
) -> dict[str, Any]:
    resultado = sanitizar_valor(
        detalle
    )

    if not isinstance(resultado, dict):
        return {}

    return resultado
