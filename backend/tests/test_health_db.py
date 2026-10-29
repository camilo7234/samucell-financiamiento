# ============================================================
# BLOQUE 1 - IMPORTACIONES
# Primero: biblioteca estandar de Python.
# Segundo: paquetes externos.
# Tercero: modulos internos del proyecto.
# ============================================================
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session
from app.main import app

client = TestClient(app)

# ============================================================
# BLOQUE 2 - SESIONES FALSAS
# Simulan la base de datos para probar el endpoint sin red.
# ============================================================
class FakeSessionOk:
    async def execute(self, *args: Any, **kwargs: Any) -> None:
        return None


# Simula un error de la capa de acceso a PostgreSQL.
class FakeSessionFail:
    async def execute(self, *args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("fallo simulado")


def override_with(fake: object) -> Callable[[], AsyncIterator[object]]:
    async def _get() -> AsyncIterator[object]:
        yield fake

    return _get


# ============================================================
# BLOQUE 3 - LIMPIEZA
# Quita los reemplazos de dependencias despues de cada prueba.
# ============================================================
@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


# ============================================================
# BLOQUE 4 - PRUEBAS
# ============================================================
def test_health_db_ok() -> None:
    app.dependency_overrides[get_session] = override_with(FakeSessionOk())

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_db_failure_returns_503_without_details() -> None:
    app.dependency_overrides[get_session] = override_with(FakeSessionFail())

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible"}
    assert "fallo simulado" not in response.text