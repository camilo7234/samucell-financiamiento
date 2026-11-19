# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.db.session import get_session
from app.modules.auth.authorization import CurrentProfile, require_role
from app.modules.credits import service
from app.modules.credits.schemas import CreditCreate, CreditResponse
from app.modules.credits.service import (
    CreditConfigurationError,
    CreditNotFoundError,
    CustomerNotFoundError,
    InventoryItemNotAvailableError,
    InventoryItemNotFoundError,
    StoreNotFoundError,
)

# ============================================================
# BLOQUE 2 - ROUTER VERSIONADO
# ============================================================
router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


# ============================================================
# BLOQUE 3 - DEPENDENCIAS DE ROL
# ============================================================
require_any_role = require_role(Role.ADMIN, Role.OPERATOR)


# ============================================================
# BLOQUE 4 - CREAR CREDITO
# ============================================================
@router.post(
    "",
    response_model=CreditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_credit(
    data: CreditCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    profile: Annotated[CurrentProfile, Depends(require_any_role)],
) -> CreditResponse:
    try:
        return await service.create_credit(
            session,
            data,
            profile.user_id,
        )
    except StoreNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sucursal no encontrada",
        ) from None
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        ) from None
    except InventoryItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        ) from None
    except InventoryItemNotAvailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El equipo no esta disponible",
        ) from None
    except CreditConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configuracion financiera invalida o tope de usura excedido",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible",
        ) from None

# ============================================================
# BLOQUE 5 - CONSULTAR CREDITO POR ID
# ============================================================
@router.get(
    "/{credit_id}",
    response_model=CreditResponse,
)
async def get_credit(
    credit_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _profile: Annotated[CurrentProfile, Depends(require_any_role)],
) -> CreditResponse:
    try:
        return await service.get_credit(session, credit_id)
    except CreditNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credito no encontrado",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible",
        ) from None