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


# ============================================================
# BLOQUE 5 - PROTECCION DE SECRETOS EN ERRORES
# Usa una URL incorrecta y una contrasena ficticia para comprobar
# que el texto de la excepcion no muestra el valor recibido.
# No utiliza ni modifica credenciales reales.
# ============================================================
def test_validation_error_hides_database_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_password = "secreto-ficticio-no-debe-aparecer"
    invalid_url = f"postgresql://usuario:{fake_password}@localhost:5432/pruebas"

    monkeypatch.setenv("DATABASE_URL", invalid_url)
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")

    with pytest.raises(ValidationError) as captured:
        Settings(_env_file=None)

    error_text = str(captured.value)

    assert "DATABASE_URL debe iniciar con postgresql+asyncpg://" in error_text
    assert fake_password not in error_text
    assert invalid_url not in error_text
    assert "input_value=" not in error_text


# ============================================================
# BLOQUE 6 - CONFIGURACION JWT
# Verifica las direcciones y restricciones de autenticacion.
# Usa valores ficticios y no realiza peticiones de red.
# ============================================================
def test_jwt_configuration_uses_project_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://usuario:clave-falsa@localhost:5432/pruebas",
    )
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co/")
    monkeypatch.setenv("JWT_ALGORITHM", "ES256")
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")

    settings = Settings(_env_file=None)

    assert settings.jwt_algorithm == "ES256"
    assert settings.jwt_audience == "authenticated"
    assert settings.jwt_issuer == "https://ejemplo.supabase.co/auth/v1"
    assert settings.jwt_jwks_url == (
        "https://ejemplo.supabase.co/auth/v1/.well-known/jwks.json"
    )