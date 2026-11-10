# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import logging
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import FORBIDDEN_DETAIL, Role, parse_role
from app.db.session import get_session
from app.modules.auth.dependencies import AuthenticatedUser, get_current_user
from app.modules.auth.profiles import fetch_profile

logger = logging.getLogger(__name__)


# ============================================================
# BLOQUE 2 - PERFIL AUTORIZADO
# Perfil activo con rol ya validado. Es lo que reciben los
# endpoints protegidos: nunca texto crudo de la base de datos.
# ============================================================
@dataclass(frozen=True, slots=True)
class CurrentProfile:
    user_id: UUID
    full_name: str
    role: Role


# ============================================================
# BLOQUE 3 - ERRORES HTTP GENERICOS
# El 403 es identico para todos los motivos. La causa real solo
# se escribe en el log del servidor, sin datos personales.
# ============================================================
def _forbidden(reason: str) -> HTTPException:
    logger.warning("Acceso denegado: motivo=%s", reason)
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=FORBIDDEN_DETAIL,
    )


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Servicio no disponible",
    )


# ============================================================
# BLOQUE 4 - DEPENDENCIA PRINCIPAL
# Encadenada con get_current_user (identidad ya verificada).
# Se consulta el perfil en cada peticion, sin cache.
# ============================================================
async def get_current_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentProfile:
    try:
        profile = await fetch_profile(session, user.user_id)
    except (SQLAlchemyError, OSError) as exc:
        logger.error("Fallo al consultar el perfil: %s", type(exc).__name__)
        raise _service_unavailable() from None

    if profile is None:
        raise _forbidden("no_profile")

    if not profile.is_active:
        raise _forbidden("inactive")

    role = parse_role(profile.role)
    if role is None:
        raise _forbidden("invalid_role")

    return CurrentProfile(
        user_id=profile.user_id,
        full_name=profile.full_name,
        role=role,
    )