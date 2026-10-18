"""Límite del cuerpo antes de analizar multipart, también sin Content-Length."""
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 2 * 1024 * 1024 + 128 * 1024

class CargaDemasiadoGrande(Exception):
    pass

class CargaUploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != "/usuarios/cargas/validar":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length:
            try:
                if int(length) < 0:
                    raise ValueError
                if int(length) > MAX_REQUEST_BYTES:
                    return await JSONResponse({"detail": "Carga superior al límite permitido."}, status_code=413)(scope, receive, send)
            except ValueError:
                return await JSONResponse({"detail": "Longitud de petición inválida."}, status_code=400)(scope, receive, send)
        total = 0
        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_REQUEST_BYTES:
                    raise CargaDemasiadoGrande
            return message
        try:
            await self.app(scope, limited_receive, send)
        except CargaDemasiadoGrande:
            await JSONResponse({"detail": "Carga superior al límite permitido."}, status_code=413)(scope, receive, send)
