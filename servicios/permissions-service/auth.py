"""Consulta online de sesión: no necesita JWT_SECRET ni claves MFA."""
import os
from dataclasses import dataclass
from urllib.parse import urlsplit
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

IAM_URL = os.getenv("IAM_BASE_URL", "http://identity:8003").rstrip("/")
parsed = urlsplit(IAM_URL)
if (parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment):
    raise RuntimeError("IAM_BASE_URL inválida")
bearer = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Actor:
    id: int

def get_actor(credentials=Depends(bearer)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Sesión requerida", headers={"WWW-Authenticate": "Bearer"})
    if len(credentials.credentials) > 8192:
        raise HTTPException(401, "Sesión inválida")
    try:
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
            response = client.get(
                IAM_URL + "/auth/me",
                headers={"Authorization": "Bearer " + credentials.credentials},
            )
        if response.status_code in {401, 403}:
            raise HTTPException(response.status_code, "Sesión no autorizada")
        if response.status_code != 200:
            raise HTTPException(503, "IAM no disponible")
        data = response.json()
        uid = data.get("id")
        if type(uid) is not int or uid <= 0 or data.get("activo") is not True:
            raise HTTPException(401, "Sesión inválida")
        if data.get("requiere_cambio_password") is not False or data.get("mfa_activo") is not True:
            raise HTTPException(403, "Complete el cambio de contraseña y MFA en IAM")
        return Actor(uid)
    except (httpx.HTTPError, ValueError, AttributeError):
        raise HTTPException(503, "No se pudo verificar la sesión") from None
