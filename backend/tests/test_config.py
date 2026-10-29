# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import pytest
from pydantic import ValidationError

from app.core.config import Settings


# ============================================================
# BLOQUE 2 - FALTAN VARIABLES OBLIGATORIAS
# _env_file=None impide leer un .env.local real durante la prueba.
# ============================================================
def test_missing_required_variables_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


# ============================================================
# BLOQUE 3 - CONFIGURACION VALIDA
# Verifica la carga y que la contrasena no se filtre en repr().
# ============================================================
def test_valid_settings_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:clave-falsa@h:5432/db")
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert "clave-falsa" not in repr(settings)


# ============================================================
# BLOQUE 4 - DRIVER INCORRECTO
# Una URL sin +asyncpg debe ser rechazada.
# ============================================================
def test_rejects_non_asyncpg_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:clave-falsa@h:5432/db")
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)