# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthTokenInvalidError
from app.main import app
from app.modules.auth.dependencies import get_token_verifier

client = TestClient(app)

USER_ID = "11111111-2222-3333-4444-555555555555"
BEARER = {"Authorization": "Bearer token-de-prueba"}


# ============================================================
# BLOQUE 2 - VERIFICADORES FALSOS Y LIMPIEZA
# ============================================================
def use_verifier(fake: Callable[[str], dict[str, Any]]) -> None:
    app.dependency_overrides[get_token_verifier] = lambda: fake


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


# ============================================================
# BLOQUE 3 - PRUEBAS
# ============================================================
def test_me_without_token_returns_401() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_invalid_token_returns_401() -> None:
    def _verify(token: str) -> dict[str, Any]:
        raise AuthTokenInvalidError("invalido")

    use_verifier(_verify)

    response = client.get("/api/v1/auth/me", headers=BEARER)

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales invalidas"}


def test_me_with_valid_token_returns_only_user_id() -> None:
    use_verifier(lambda token: {"sub": USER_ID, "email": "privado@example.com"})

    response = client.get("/api/v1/auth/me", headers=BEARER)

    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID}
    assert "privado@example.com" not in response.text


def test_health_remains_public() -> None:
    response = client.get("/health")

    assert response.status_code == 200