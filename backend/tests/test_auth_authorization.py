# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.permissions import FORBIDDEN_DETAIL
from app.db.session import get_session
from app.modules.auth import authorization
from app.modules.auth.authorization import CurrentProfile, get_current_profile
from app.modules.auth.dependencies import AuthenticatedUser, get_current_user
from app.modules.auth.profiles import Profile

USER_ID = UUID("22222222-2222-2222-2222-222222222222")
FULL_NAME = "Nombre Privado"


# ============================================================
# BLOQUE 2 - APLICACION DE PRUEBA Y FALSOS
# probe_app expone una ruta protegida solo para las pruebas.
# ============================================================
async def fake_session() -> AsyncIterator[object]:
    yield object()


def fake_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=USER_ID, claims={})


def build_client(*, authenticated: bool = True) -> TestClient:
    probe_app = FastAPI()

    @probe_app.get("/probe")
    async def probe(
        profile: Annotated[CurrentProfile, Depends(get_current_profile)],
    ) -> dict[str, str]:
        return {"role": profile.role.value}

    if authenticated:
        probe_app.dependency_overrides[get_current_user] = fake_user
    probe_app.dependency_overrides[get_session] = fake_session
    return TestClient(probe_app)


def patch_fetch(monkeypatch: pytest.MonkeyPatch, result: object) -> None:
    async def fake_fetch(session: object, user_id: UUID) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(authorization, "fetch_profile", fake_fetch)


def make_profile(role: str, *, is_active: bool = True) -> Profile:
    return Profile(
        user_id=USER_ID, full_name=FULL_NAME, role=role, is_active=is_active
    )


# ============================================================
# BLOQUE 3 - PERFILES AUTORIZADOS
# ============================================================
@pytest.mark.parametrize("role", ["admin", "operator"])
def test_active_profile_is_authorized(
    monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    patch_fetch(monkeypatch, make_profile(role))

    response = build_client().get("/probe")

    assert response.status_code == 200
    assert response.json() == {"role": role}


# ============================================================
# BLOQUE 4 - 403 IDENTICO PARA TODOS LOS MOTIVOS
# Mismo codigo, mismo cuerpo, sin WWW-Authenticate. El motivo
# queda en el log, sin user_id ni nombre.
# ============================================================
@pytest.mark.parametrize(
    ("reason", "profile"),
    [
        ("no_profile", None),
        ("inactive", make_profile("admin", is_active=False)),
        ("invalid_role", make_profile("superuser")),
    ],
)
def test_denied_profile_returns_generic_403(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    reason: str,
    profile: Profile | None,
) -> None:
    patch_fetch(monkeypatch, profile)

    with caplog.at_level(logging.WARNING):
        response = build_client().get("/probe")

    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    assert "www-authenticate" not in response.headers
    assert reason in caplog.text
    assert str(USER_ID) not in caplog.text
    assert FULL_NAME not in caplog.text


# ============================================================
# BLOQUE 5 - FALLO DE BASE DE DATOS
# 503 generico; ni el texto del error ni secretos llegan al cliente.
# ============================================================
@pytest.mark.parametrize(
    "error",
    [SQLAlchemyError("secreto-db"), OSError("secreto-db")],
)
def test_database_failure_returns_503_without_details(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    patch_fetch(monkeypatch, error)

    response = build_client().get("/probe")

    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}
    assert "secreto-db" not in response.text


# ============================================================
# BLOQUE 6 - SIN TOKEN: EL 401 VA ANTES QUE CUALQUIER 403
# ============================================================
def test_missing_token_returns_401_before_profile_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_fetch(monkeypatch, make_profile("admin"))

    response = build_client(authenticated=False).get("/probe")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"