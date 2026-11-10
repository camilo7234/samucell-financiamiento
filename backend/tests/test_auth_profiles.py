# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.modules.auth.profiles import Profile, fetch_profile

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


# ============================================================
# BLOQUE 2 - SESION FALSA
# execute() devuelve un resultado cuyo mappings().first() entrega
# la fila indicada (o None).
# ============================================================
def make_session(row: dict | None) -> AsyncMock:
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    session = AsyncMock()
    session.execute.return_value = result
    return session


# ============================================================
# BLOQUE 3 - PERFIL ENCONTRADO
# ============================================================
@pytest.mark.asyncio
async def test_fetch_profile_returns_profile() -> None:
    row = {
        "id": USER_ID,
        "full_name": "Usuario de Prueba",
        "role": "admin",
        "is_active": True,
    }
    session = make_session(row)

    profile = await fetch_profile(session, USER_ID)

    assert profile == Profile(
        user_id=USER_ID,
        full_name="Usuario de Prueba",
        role="admin",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_fetch_profile_keeps_raw_role_and_inactive_flag() -> None:
    row = {
        "id": USER_ID,
        "full_name": "Otro Usuario",
        "role": "valor-raro",
        "is_active": False,
    }
    session = make_session(row)

    profile = await fetch_profile(session, USER_ID)

    assert profile is not None
    assert profile.role == "valor-raro"
    assert profile.is_active is False


# ============================================================
# BLOQUE 4 - PERFIL INEXISTENTE
# ============================================================
@pytest.mark.asyncio
async def test_fetch_profile_returns_none_when_missing() -> None:
    session = make_session(None)

    assert await fetch_profile(session, USER_ID) is None


# ============================================================
# BLOQUE 5 - CONSULTA SEGURA
# Parametrizada, de solo lectura y sin el id dentro del SQL.
# ============================================================
@pytest.mark.asyncio
async def test_fetch_profile_query_is_parameterized_select() -> None:
    session = make_session(None)

    await fetch_profile(session, USER_ID)

    statement, params = session.execute.call_args.args
    sql = str(statement)
    assert params == {"user_id": USER_ID}
    assert sql.lstrip().upper().startswith("SELECT")
    assert ":user_id" in sql
    assert str(USER_ID) not in sql
    assert "*" not in sql