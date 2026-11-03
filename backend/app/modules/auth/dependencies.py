# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import (
    AuthTokenInvalidError,
    KeysUnavailableError,
    verify_access_token,
)

# ============================================================
# BLOQUE 2 - ESQUEMA BEARER
# auto_error=False: nosotros decidimos la respuesta, para que
# un encabezado ausente o mal formado devuelva siempre 401.
# ============================================================
bearer_scheme = HTTPBearer(auto_error=False)

TokenVerifier = Callable[[str], dict[str, Any]]


# ============================================================
# BLOQUE 3 - USUARIO AUTENTICADO
# Datos minimos y de solo lectura. El rol de negocio (admin u
# operator) NO sale del token: se consultara en profiles.
# ============================================================
@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: UUID
    claims: dict[str, Any]


# ============================================================
# BLOQUE 4 - VERIFICADOR INYECTABLE
# Las pruebas reemplazan esta dependencia por una falsa.
# ============================================================
def get_token_verifier() -> TokenVerifier:
    return verify_access_token


# ============================================================
# BLOQUE 5 - ERRORES HTTP GENERICOS
# Sin detalles internos, sin eco del token.
# ============================================================
def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================
# BLOQUE 6 - DEPENDENCIA PRINCIPAL
# Es sincrona a proposito: FastAPI la ejecuta en un hilo y la
# descarga del JWKS (bloqueante) no congela el servidor.
# ============================================================
def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthenticatedUser:
    if credentials is None:
        raise _unauthorized()

    try:
        claims = verifier(credentials.credentials)
    except AuthTokenInvalidError:
        raise _unauthorized() from None
    except KeysUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de autenticacion no disponible",
        ) from None

    try:
        user_id = UUID(str(claims["sub"]))
    except (KeyError, ValueError):
        raise _unauthorized() from None

    return AuthenticatedUser(user_id=user_id, claims=claims)