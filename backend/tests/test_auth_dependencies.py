# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from collections.abc import Callable, Iterator
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import AuthTokenInvalidError, KeysUnavailableError
from app.modules.auth.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_token_verifier,
)

USER_ID = "11111111-2222-3333-4444-555555555555"

# ============================================================
# BLOQUE 2 - APLICACION MINIMA DE PRUEBA
# No usa app.main: aisla la dependencia de cualquier otro modulo.
# ============================================================
probe_app = FastAPI()


@probe_app.get("/whoami")
def whoami(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, str]:
    return {"user_id": str(user.user_id)}


client = TestClient(probe_app)


# ============================================================
# BLOQUE 3 - VERIFICADORES FALSOS Y LIMPIEZA
# ============================================================
def verifier_returning(claims: dict[str, Any]) -> Callable[[str], dict[str, Any]]:
    def _verify(token: str) -> dict[str, Any]:
        return claims

    return _verify


def verifier_raising(exc: Exception) -> Callable[[str], dict[str, Any]]:
    def _verify(token: str) -> dict[str, Any]:
        raise exc

    return _verify


def use_verifier(fake: Callable[[str], dict[str, Any]]) -> None:
    probe_app.dependency_overrides[get_token_verifier] = lambda: fake


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    probe_app.dependency_overrides.clear()


BEARER = {"Authorization": "Bearer token-de-prueba"}


# ============================================================
# BLOQUE 4 - RECHAZOS 401
# ============================================================
def test_missing_header_returns_401() -> None:
    use_verifier(verifier_returning({"sub": USER_ID}))

    response = client.get("/whoami")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Credenciales invalidas"}


def test_non_bearer_scheme_returns_401() -> None:
    use_verifier(verifier_returning({"sub": USER_ID}))

    response = client.get("/whoami", headers={"Authorization": "Basic abc123"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_returns_401_without_echo() -> None:
    use_verifier(verifier_raising(AuthTokenInvalidError("detalle interno")))

    response = client.get("/whoami", headers=BEARER)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Credenciales invalidas"}
    assert "detalle interno" not in response.text
    assert "token-de-prueba" not in response.text


@pytest.mark.parametrize("claims", [{}, {"sub": "no-es-uuid"}, {"sub": ""}])
def test_unusable_subject_returns_401(claims: dict[str, Any]) -> None:
    use_verifier(verifier_returning(claims))

    response = client.get("/whoami", headers=BEARER)

    assert response.status_code == 401


# ============================================================
# BLOQUE 5 - FALLO DE CLAVES: 503
# ============================================================
def test_keys_unavailable_returns_503_without_details() -> None:
    use_verifier(verifier_raising(KeysUnavailableError("jwks caido")))

    response = client.get("/whoami", headers=BEARER)

    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio de autenticacion no disponible"}
    assert "jwks caido" not in response.text


# ============================================================
# BLOQUE 6 - CASO VALIDO
# Ademas comprueba que el verificador recibe el token sin el
# prefijo "Bearer".
# ============================================================
def test_valid_token_returns_user_id() -> None:
    received: list[str] = []

    def _verify(token: str) -> dict[str, Any]:
        received.append(token)
        return {"sub": USER_ID}

    use_verifier(_verify)

    response = client.get("/whoami", headers=BEARER)

    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID}
    assert received == ["token-de-prueba"]