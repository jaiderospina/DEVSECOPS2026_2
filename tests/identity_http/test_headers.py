"""Exercise HTTP responses and CORS with the production header middleware.
No imports of Identity auth/database, no .env reads or real credentials.
"""
import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx

path = Path(__file__).resolve().parents[2] / "servicios/identity-service/http_headers.py"
spec = importlib.util.spec_from_file_location("iam_http_headers", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def client():
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"estado": "funcionando"}

    @app.get("/protected")
    async def protected():
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/number")
    async def number(value: int):
        return {"value": value}

    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                       allow_credentials=True, allow_methods=["GET"],
                       allow_headers=["Authorization"])
    app.add_middleware(module.ApiSecurityHeadersMiddleware)
    class LocalClient:
        def request(self, method, path, **kwargs):
            async def execute():
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                ) as session:
                    return await session.request(method, path, **kwargs)
            return asyncio.run(execute())

        def get(self, path, **kwargs):
            return self.request("GET", path, **kwargs)

        def options(self, path, **kwargs):
            return self.request("OPTIONS", path, **kwargs)

    return LocalClient()


@pytest.mark.parametrize("path,status", [("/", 200), ("/protected", 401),
                                        ("/missing", 404), ("/number?value=bad", 422)])
def test_headers_preserve_status_and_json(client, path, status):
    response = client.get(path)
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    if status == 401:
        assert response.headers["www-authenticate"] == "Bearer"


def test_allowed_origin_preflight_keeps_security_headers(client):
    response = client.options("/protected", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_untrusted_origin_does_not_gain_cors_access(client):
    response = client.get("/", headers={"Origin": "https://untrusted.invalid"})
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
