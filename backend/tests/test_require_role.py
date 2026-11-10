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

from app.core.permissions import FORBIDDEN_DETAIL, Role
from app.db.session import get_session
from app.modules.auth import authorization
from app.modules.auth.authorization import CurrentProfile, require_role
from app.modules.auth.dependencies import AuthenticatedUser, get_current_user
from app.modules.auth.profiles import Profile

USER_ID = UUID("33333333-3333-3333-3333-333333333333")
FULL_NAME = "Nombre Privado"


# ============================================================
# BLOQUE 2 - APLICACION DE PRUEBA Y FALSOS
# ============================================================
async def fake_session() -> AsyncIterator[object]:
    yield object()


def fake_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=USER_ID, claims={})


def build_client(*roles: Role) -> TestClient:
    probe_app = FastAPI()

    @probe_app.get("/probe")
    async def probe(
        profile: Annotated[CurrentProfile, Depends(require_role(*roles))],
    ) -> dict[str, str]:
        return {"role": profile.role.value}

    probe_app.dependency_overrides[get_current_user] = fake_user
    probe_app.dependency_overrides[get_session] = fake_session
    return TestClient(probe_app)


def patch_fetch(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    async def fake_fetch(session: object, user_id: UUID) -> Profile:
        return Profile(
            user_id=USER_ID, full_name=FULL_NAME, role=role, is_active=True
        )

    monkeypatch.setattr(authorization, "fetch_profile", fake_fetch)


# ============================================================
# BLOQUE 3 - ROL PERMITIDO
# ============================================================
def test_admin_is_allowed_on_admin_route(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, "admin")

    response = build_client(Role.ADMIN).get("/probe")

    assert response.status_code == 200
    assert response.json() == {"role": "admin"}


def test_multiple_roles_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, "operator")

    response = build_client(Role.ADMIN, Role.OPERATOR).get("/probe")

    assert response.status_code == 200
    assert response.json() == {"role": "operator"}


# ============================================================
# BLOQUE 4 - ROL INSUFICIENTE: MISMO 403 GENERICO
# ============================================================
def test_operator_is_denied_on_admin_route(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    patch_fetch(monkeypatch, "operator")

    with caplog.at_level(logging.WARNING):
        response = build_client(Role.ADMIN).get("/probe")

    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    assert "www-authenticate" not in response.headers
    assert "insufficient_role" in caplog.text
    assert str(USER_ID) not in caplog.text
    assert FULL_NAME not in caplog.text


# ============================================================
# BLOQUE 5 - CONFIGURACION INVALIDA
# ============================================================
def test_require_role_without_roles_fails_at_build_time() -> None:
    with pytest.raises(ValueError):
        require_role()