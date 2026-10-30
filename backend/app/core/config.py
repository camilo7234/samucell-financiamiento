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
        extra="ignore",
        hide_input_in_errors=True,
    )

    # Entorno de ejecucion. Por defecto, desarrollo.
    app_env: Literal["development", "staging", "production"] = "development"

    # URL del Session Pooler de Supabase. SecretStr evita que la
    # contrasena aparezca en logs o en repr().
    database_url: SecretStr

    # URL publica del proyecto Supabase.
    supabase_url: AnyHttpUrl

    # ========================================================
    # BLOQUE 3.1 - PARAMETROS DE VALIDACION JWT
    # Solo admitimos ES256 para las nuevas sesiones del proyecto.
    # La audiencia identifica los tokens de usuarios autenticados.
    # ========================================================
    jwt_algorithm: Literal["ES256"] = "ES256"
    jwt_audience: Literal["authenticated"] = "authenticated"

    # ========================================================
    # BLOQUE 3.2 - EMISOR ESPERADO
    # Se deriva de SUPABASE_URL para no duplicar configuracion.
    # rstrip evita generar dos barras antes de "auth/v1".
    # ========================================================
    @property
    def jwt_issuer(self) -> str:
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1"

    # ========================================================
    # BLOQUE 3.3 - DIRECCION DE LAS CLAVES PUBLICAS
    # El verificador consultara esta URL de confianza.
    # Nunca se tomara una URL de claves desde el token recibido.
    # ========================================================
    @property
    def jwt_jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"

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