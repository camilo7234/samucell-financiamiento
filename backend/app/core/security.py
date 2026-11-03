# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import logging
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ============================================================
# BLOQUE 2 - EXCEPCIONES PROPIAS
# AuthTokenInvalidError  -> el token es malo (la API respondera 401).
# KeysUnavailableError   -> no se pudieron obtener las claves
#                           publicas (la API respondera 503).
# ============================================================
class AuthTokenInvalidError(Exception):
    """Token ausente, malformado, expirado o no confiable."""


class KeysUnavailableError(Exception):
    """No fue posible consultar el JWKS del proyecto."""


# ============================================================
# BLOQUE 3 - CLAIMS OBLIGATORIOS Y TOLERANCIA DE RELOJ
# Un token sin alguno de estos claims se rechaza.
# ============================================================
REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub"]
CLOCK_LEEWAY_SECONDS = 10


# ============================================================
# BLOQUE 4 - CLIENTE JWKS
# La URL sale siempre de Settings, nunca del token.
# PyJWKClient guarda las claves en cache y elige la correcta
# por el "kid" del encabezado del token.
# ============================================================
@lru_cache
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(settings.jwt_jwks_url, timeout=5)


# ============================================================
# BLOQUE 5 - VERIFICADOR
# Devuelve los claims solo si firma, algoritmo, expiracion,
# emisor, audiencia y sujeto son validos.
# Los parametros opcionales permiten inyectar configuracion y
# claves ficticias en las pruebas, sin red.
# ============================================================
def verify_access_token(
    token: str,
    *,
    settings: Settings | None = None,
    jwks_client: PyJWKClient | None = None,
) -> dict[str, Any]:
    if not token or not token.strip():
        raise AuthTokenInvalidError("Token ausente")

    settings = settings or get_settings()
    jwks_client = jwks_client or get_jwks_client()

    # 5.1 - Obtener la clave publica que corresponde al token.
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError as exc:
        logger.error("JWKS no disponible: %s", type(exc).__name__)
        raise KeysUnavailableError("No se pudo consultar el JWKS") from exc
    except (PyJWKClientError, jwt.PyJWTError) as exc:
        logger.info("Token rechazado al buscar clave: %s", type(exc).__name__)
        raise AuthTokenInvalidError("Token invalido") from exc

    # 5.2 - Verificar firma y claims con algoritmo fijado.
    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=CLOCK_LEEWAY_SECONDS,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as exc:
        logger.info("Token rechazado: %s", type(exc).__name__)
        raise AuthTokenInvalidError("Token invalido") from exc

    # 5.3 - El sujeto debe ser un texto no vacio.
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise AuthTokenInvalidError("Token sin sujeto valido")

    return claims