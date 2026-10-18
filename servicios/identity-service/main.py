import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from autenticacion import router as autenticacion_router
from companias import router as companias_router
from usuarios import router as usuarios_router
from cargas_usuarios import router as cargas_router
from auditoria_reportes import router as auditoria_reportes_router
from cargas_limite import CargaUploadLimitMiddleware
from http_headers import ApiSecurityHeadersMiddleware


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
# Cargamos variables de entorno antes de construir la
# configuración CORS.
#
# CORS_ORIGINS permite que el mismo código pueda ejecutarse
# en diferentes computadores/entornos sin hardcodear una IP
# particular dentro de main.py.
#
# Ejemplo de configuración para una demostración en LAN:
#
# CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.X.X:5173
#
# La IP real se configura en el entorno, no en el repositorio.
# No se utiliza "*" porque la aplicación maneja autenticación.
# =========================================================

load_dotenv()


def obtener_origenes_cors() -> list[str]:
    """
    Obtiene y normaliza la lista de orígenes permitidos.

    SEGURIDAD:
    - no habilita todos los orígenes indiscriminadamente;
    - elimina espacios;
    - elimina barras finales para evitar inconsistencias;
    - elimina duplicados;
    - conserva localhost/127.0.0.1 como valores de desarrollo
      cuando CORS_ORIGINS no está configurado.
    """

    valor = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    origenes = []
    vistos = set()

    for origen in valor.split(","):
        origen_normalizado = origen.strip().rstrip("/")

        if not origen_normalizado:
            continue

        # FastAPI/Starlette espera orígenes HTTP(S).
        # Rechazamos silenciosamente entradas que no tengan
        # un esquema web válido.
        if not origen_normalizado.startswith(
            ("http://", "https://")
        ):
            continue

        if origen_normalizado not in vistos:
            origenes.append(origen_normalizado)
            vistos.add(origen_normalizado)

    if not origenes:
        raise RuntimeError(
            "CORS_ORIGINS no contiene ningún origen HTTP(S) válido"
        )

    return origenes


CORS_ORIGINS = obtener_origenes_cors()


# =========================================================
# APLICACIÓN PRINCIPAL - IDENTITY SERVICE
# =========================================================

app = FastAPI(
    title="Identity Service",
    version="1.0.0",
)


# =========================================================
# MANEJO SEGURO DE ERRORES DE VALIDACIÓN
# =========================================================
# FastAPI/Pydantic puede incluir el valor recibido dentro del
# campo "input" de los errores HTTP 422.
#
# En un servicio de identidad dicho valor podría ser una
# contraseña, contraseña temporal u otro dato sensible.
#
# Por eso devolvemos únicamente metadatos de validación.
# Nunca devolvemos:
# - input;
# - body;
# - contraseña;
# - token;
# - hash;
# - secretos.
# =========================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errores_sanitizados = []

    for error in exc.errors():
        error_seguro = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
        }

        # ctx puede contener objetos no serializables en ciertos
        # tipos de error. Solo copiamos valores simples que son
        # útiles para la interfaz y que no proceden del campo
        # "input" enviado por el usuario.
        contexto = error.get("ctx")

        if contexto:
            contexto_seguro = {}

            for clave, valor in contexto.items():
                if isinstance(
                    valor,
                    (str, int, float, bool, type(None)),
                ):
                    contexto_seguro[clave] = valor

            if contexto_seguro:
                error_seguro["ctx"] = contexto_seguro

        errores_sanitizados.append(error_seguro)

    return JSONResponse(
        status_code=422,
        content={"detail": errores_sanitizados},
    )


# =========================================================
# CORS
# =========================================================
# Los orígenes se obtienen desde CORS_ORIGINS.
#
# Esto resuelve dos escenarios:
#
# 1. Desarrollo local:
#    http://localhost:5173
#    http://127.0.0.1:5173
#
# 2. Demostración desde otro computador:
#    se agrega el origen real del frontend mediante variable
#    de entorno, sin modificar el código fuente.
#
# IMPORTANTE:
# - No usamos allow_origins=["*"].
# - La lista debe contener exclusivamente los frontends que
#   deban comunicarse con Identity Service.
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Headers tambien en respuestas CORS y errores HTTP manejados.
app.add_middleware(CargaUploadLimitMiddleware)
app.add_middleware(ApiSecurityHeadersMiddleware)

# =========================================================
# ROUTERS
# =========================================================

app.include_router(autenticacion_router)
app.include_router(cargas_router)
app.include_router(auditoria_reportes_router)
app.include_router(usuarios_router)
app.include_router(companias_router)


# =========================================================
# HEALTH CHECK BÁSICO
# =========================================================
# Este endpoint permite comprobar que Identity Service está
# disponible sin exponer configuración, secretos ni datos de
# usuarios.
# =========================================================

@app.get("/")
def inicio():
    return {
        "servicio": "identity",
        "estado": "funcionando",
    }
