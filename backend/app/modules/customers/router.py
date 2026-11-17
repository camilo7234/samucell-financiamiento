# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.db.session import get_session
from app.modules.auth.authorization import require_role
from app.modules.customers import service
from app.modules.customers.service import (
    CustomerAlreadyExistsError,
    CustomerCreate,
    CustomerNotFoundError,
    CustomerResponse,
    CustomerUpdate,
)

# ============================================================
# BLOQUE 2 - ROUTER VERSIONADO
# ============================================================
router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

# ============================================================
# BLOQUE 3 - DEPENDENCIAS DE ROL
# ============================================================
require_any_role = require_role(Role.ADMIN, Role.OPERATOR)

# ============================================================
# BLOQUE 4 - CREAR CLIENTE
# ============================================================
@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _profile: Annotated[object, Depends(require_any_role)],
) -> CustomerResponse:
    try:
        return await service.create_customer(session, data)
    except CustomerAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya existe",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible",
        ) from None

# ============================================================
# BLOQUE 5 - CONSULTAR POR ID
# ============================================================
@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _profile: Annotated[object, Depends(require_any_role)],
) -> CustomerResponse:
    try:
        return await service.get_customer(session, customer_id)
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible",
        ) from None

# ============================================================
# BLOQUE 6 - BUSCAR POR DOCUMENTO O NOMBRE
# ============================================================
@router.get("", response_model=list[CustomerResponse])
async def find_customers(
    session: Annotated[AsyncSession, Depends(get_session)],
    _profile: Annotated[object, Depends(require_any_role)],
    document_type: str | None = Query(default=None, pattern="^(CC|CE|NIT|PAS)$"),
    document_number: str | None = Query(default=None, min_length=1, max_length=50),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[CustomerResponse]:
    if document_type and document_number:
        customer = await service.find_customer_by_document(
            session, document_type, document_number
        )
        return [customer] if customer else []
    if q:
        return await service.find_customers_by_name(session, q, limit)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Debe indicar document_type y document_number, o q",
    )

# ============================================================
# BLOQUE 7 - ACTUALIZAR CLIENTE
# ============================================================
@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _profile: Annotated[object, Depends(require_any_role)],
) -> CustomerResponse:
    try:
        return await service.update_customer(session, customer_id, data)
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible",
        ) from None