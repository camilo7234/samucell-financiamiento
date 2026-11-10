# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import pytest

from app.core.permissions import FORBIDDEN_DETAIL, Role, parse_role


# ============================================================
# BLOQUE 2 - ROLES VALIDOS
# ============================================================
def test_role_values_match_database_check() -> None:
    assert {role.value for role in Role} == {"admin", "operator"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("admin", Role.ADMIN), ("operator", Role.OPERATOR)],
)
def test_parse_role_accepts_valid_values(raw: str, expected: Role) -> None:
    assert parse_role(raw) is expected


# ============================================================
# BLOQUE 3 - ROLES INVALIDOS
# ============================================================
@pytest.mark.parametrize(
    "raw",
    ["", " ", "Admin", "ADMIN", " admin", "admin ", "superuser", None, 1, b"admin"],
)
def test_parse_role_rejects_invalid_values(raw: object) -> None:
    assert parse_role(raw) is None


# ============================================================
# BLOQUE 4 - MENSAJE GENERICO
# ============================================================
def test_forbidden_detail_is_generic() -> None:
    assert FORBIDDEN_DETAIL == "Acceso denegado"