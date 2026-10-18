"""HTTP response policy for Audit Service."""
from starlette.datastructures import MutableHeaders


class ApiSecurityHeadersMiddleware:
    """Add browser hardening without changing response bodies or status codes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
            await send(message)

        await self.app(scope, receive, send_with_headers)
