import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request
from urllib.parse import urlsplit
from http.client import HTTPConnection, HTTPSConnection
from contextlib import contextmanager

from dotenv import load_dotenv


# ============================================================
# IAM SECURE - AUDIT DISPATCHER
# CLIENTE INTERNO DE AUDIT SERVICE
# ============================================================
#
# Nunca registra:
# - token interno;
# - cuerpo de eventos;
# - respuestas completas;
# - credenciales.
# ============================================================

load_dotenv()


@contextmanager
def urlopen(request: Request, timeout: float):
    """HTTP(S) only; never follow redirects carrying the internal token."""
    url = urlsplit(request.full_url)
    if (url.scheme not in ("http", "https") or not url.hostname
            or url.username is not None or url.password is not None
            or url.fragment):
        raise ValueError("AUDIT_SERVICE_URL debe ser HTTP(S) sin credenciales ni fragmento")
    connection_type = HTTPSConnection if url.scheme == "https" else HTTPConnection
    connection = connection_type(url.hostname, port=url.port, timeout=timeout)
    try:
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        connection.request(request.get_method(), path, body=request.data,
                           headers=dict(request.header_items()))
        response = connection.getresponse()
        if response.status >= 400:
            raise HTTPError(request.full_url, response.status,
                            "Audit HTTP error", response.headers, None)
        yield response
    finally:
        connection.close()


AUDIT_SERVICE_URL = os.getenv(
    "AUDIT_SERVICE_URL",
    "",
).strip().rstrip("/")

AUDIT_INTERNAL_TOKEN = os.getenv(
    "AUDIT_INTERNAL_TOKEN",
    "",
).strip()


if not AUDIT_SERVICE_URL:
    raise RuntimeError(
        "AUDIT_SERVICE_URL no esta configurado"
    )

if len(AUDIT_INTERNAL_TOKEN) < 32:
    raise RuntimeError(
        "AUDIT_INTERNAL_TOKEN no esta configurado correctamente"
    )


try:
    AUDIT_HTTP_TIMEOUT_SECONDS = float(
        os.getenv(
            "AUDIT_HTTP_TIMEOUT_SECONDS",
            "3",
        )
    )
except ValueError as exc:
    raise RuntimeError(
        "AUDIT_HTTP_TIMEOUT_SECONDS debe ser numerico"
    ) from exc


def enviar_evento(evento: dict) -> tuple[bool, str]:
    """
    Entrega un evento al Audit Service.

    Retorna un resultado seguro para que el worker pueda decidir
    si completa o reintenta el trabajo.
    """

    try:
        cuerpo = json.dumps(
            evento,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        solicitud = Request(
            url=f"{AUDIT_SERVICE_URL}/eventos",
            data=cuerpo,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-IAM-Audit-Token":
                    AUDIT_INTERNAL_TOKEN,
            },
        )

        with urlopen(
            solicitud,
            timeout=AUDIT_HTTP_TIMEOUT_SECONDS,
        ) as respuesta:
            codigo = respuesta.status

        if codigo in (200, 201):
            return True, "OK"

        return False, f"HTTP_{codigo}"

    except HTTPError as exc:
        return False, f"HTTP_{exc.code}"

    except URLError:
        return False, "AUDIT_SERVICE_NO_DISPONIBLE"

    except TimeoutError:
        return False, "AUDIT_SERVICE_TIMEOUT"

    except OSError:
        return False, "AUDIT_SERVICE_ERROR_RED"

    except Exception:
        return False, "AUDIT_SERVICE_ERROR_INTERNO"
