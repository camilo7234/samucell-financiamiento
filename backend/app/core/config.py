# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================
# BLOQUE 2 - RUTA DEL ARCHIVO DE SECRETOS
# Apunta a backend/.env.local sin depender de desde que carpeta
# se ejecute el programa. Este archivo NO se versiona en Git.
# ============================================================
ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"


# ============================================================
# BLOQUE 3 - DEFINICION DE LA CONFIGURACION
# Las variables sin valor por defecto son OBLIGATORIAS: si faltan,
# la aplicacion no arranca y el error indica cual falta.
# ============================================================
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # ignora variables que no usamos todavia
    )

    # Entorno de ejecucion. Por defecto, desarrollo.
    app_env: Literal["development", "staging", "production"] = "development"

    # URL del Session Pooler de Supabase. SecretStr evita que la
    # contrasena aparezca en logs o en repr().
    database_url: SecretStr

    # URL publica del proyecto Supabase.
    supabase_url: AnyHttpUrl

    # ========================================================
    # BLOQUE 4 - VALIDACION DEL DRIVER
    # SQLAlchemy async exige el prefijo postgresql+asyncpg://
    # ========================================================
    @field_validator("database_url")
    @classmethod
    def validate_async_driver(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL debe iniciar con postgresql+asyncpg://")
        return value


# ============================================================
# BLOQUE 5 - ACCESO UNICO A LA CONFIGURACION
# lru_cache crea el objeto una sola vez. No se instancia al
# importar el modulo, asi las pruebas pueden controlar el entorno.
# ============================================================
@lru_cache
def get_settings() -> Settings:
    return Settings()