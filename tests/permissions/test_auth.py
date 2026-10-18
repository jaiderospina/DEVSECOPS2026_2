"""Contrato HTTP entre Permissions e IAM. No se usan tokens reales."""
import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import auth

REAL_CLIENT = httpx.Client
CREDS = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-session")
VALID = {"id": 2, "activo": True, "mfa_activo": True, "requiere_cambio_password": False}

def mock_iam(monkeypatch, status=200, data=None):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, json=VALID if data is None else data)
    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False
        assert kwargs["timeout"] == 5
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(auth.httpx, "Client", client)
    return requests

def test_valid_session_is_checked_online(monkeypatch):
    requests = mock_iam(monkeypatch)
    assert auth.get_actor(CREDS).id == 2
    assert str(requests[0].url).endswith("/auth/me")
    assert requests[0].headers["Authorization"] == "Bearer test-session"
    assert requests[0].url.query == b""

@pytest.mark.parametrize("status,expected", [(401, 401), (403, 403), (302, 503), (500, 503)])
def test_invalid_or_unavailable_iam_never_authorizes(monkeypatch, status, expected):
    mock_iam(monkeypatch, status=status)
    with pytest.raises(HTTPException) as error:
        auth.get_actor(CREDS)
    assert error.value.status_code == expected

@pytest.mark.parametrize("data,expected", [
    ({**VALID, "mfa_activo": False}, 403),
    ({**VALID, "requiere_cambio_password": True}, 403),
    ({**VALID, "activo": False}, 401),
    ({**VALID, "id": True}, 401),
    ({"id": 2}, 401),
])
def test_incomplete_security_context_is_rejected(monkeypatch, data, expected):
    mock_iam(monkeypatch, data=data)
    with pytest.raises(HTTPException) as error:
        auth.get_actor(CREDS)
    assert error.value.status_code == expected

def test_network_error_is_sanitized(monkeypatch):
    def client(**kwargs):
        def handler(request):
            raise httpx.ConnectError("internal detail must not be exposed", request=request)
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(auth.httpx, "Client", client)
    with pytest.raises(HTTPException) as error:
        auth.get_actor(CREDS)
    assert error.value.status_code == 503
    assert "internal detail" not in error.value.detail

def test_missing_bearer_is_denied():
    with pytest.raises(HTTPException) as error:
        auth.get_actor(None)
    assert error.value.status_code == 401
