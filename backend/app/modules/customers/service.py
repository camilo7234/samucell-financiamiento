# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================
# BLOQUE 2 - ERRORES DE NEGOCIO
# ============================================================
class CustomerNotFoundError(Exception):
    pass


class CustomerAlreadyExistsError(Exception):
    pass


# ============================================================
# BLOQUE 3 - ESQUEMAS DE ENTRADA Y SALIDA
# ============================================================
class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    document_type: str = Field(pattern="^(CC|CE|NIT|PAS)$")
    document_number: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|inactive|blocked)$")
    notes: str | None = Field(default=None, max_length=1000)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    document_type: str
    document_number: str
    phone: str
    address: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# BLOQUE 4 - CONSULTAS PARAMETRIZADAS
# ============================================================
_INSERT_QUERY = text(
    "INSERT INTO public.customers "
    "(full_name, document_type, document_number, phone, address, notes) "
    "VALUES (:full_name, :document_type, :document_number, :phone, :address, :notes) "
    "RETURNING id, full_name, document_type, document_number, phone, address, "
    "status, notes, created_at, updated_at"
)

_SELECT_BY_ID_QUERY = text(
    "SELECT id, full_name, document_type, document_number, phone, address, "
    "status, notes, created_at, updated_at "
    "FROM public.customers "
    "WHERE id = :customer_id"
)

_SELECT_BY_DOCUMENT_QUERY = text(
    "SELECT id, full_name, document_type, document_number, phone, address, "
    "status, notes, created_at, updated_at "
    "FROM public.customers "
    "WHERE document_type = :document_type AND document_number = :document_number"
)

_SELECT_BY_NAME_QUERY = text(
    "SELECT id, full_name, document_type, document_number, phone, address, "
    "status, notes, created_at, updated_at "
    "FROM public.customers "
    "WHERE lower(full_name) LIKE lower(:pattern) "
    "ORDER BY full_name "
    "LIMIT :limit"
)

_UPDATE_QUERY = text(
    "UPDATE public.customers "
    "SET full_name = COALESCE(:full_name, full_name), "
    "phone = COALESCE(:phone, phone), "
    "address = COALESCE(:address, address), "
    "status = COALESCE(:status, status), "
    "notes = COALESCE(:notes, notes) "
    "WHERE id = :customer_id "
    "RETURNING id, full_name, document_type, document_number, phone, address, "
    "status, notes, created_at, updated_at"
)

# ============================================================
# BLOQUE 5 - CREAR CLIENTE
# ============================================================
async def create_customer(
    session: AsyncSession, data: CustomerCreate
) -> CustomerResponse:
    try:
        result = await session.execute(
            _INSERT_QUERY,
            {
                "full_name": data.full_name,
                "document_type": data.document_type,
                "document_number": data.document_number,
                "phone": data.phone,
                "address": data.address,
                "notes": data.notes,
            },
        )
    except SQLAlchemyError as exc:
        if "customers_document_type_document_number_key" in str(exc):
            raise CustomerAlreadyExistsError() from None
        raise

    row = result.mappings().first()
    if row is None:
        raise CustomerNotFoundError()

    await session.commit()

    return CustomerResponse.model_validate(row)

# ============================================================
# BLOQUE 6 - CONSULTAR POR ID
# ============================================================
async def get_customer(
    session: AsyncSession, customer_id: UUID
) -> CustomerResponse:
    result = await session.execute(
        _SELECT_BY_ID_QUERY, {"customer_id": customer_id}
    )
    row = result.mappings().first()
    if row is None:
        raise CustomerNotFoundError()

    return CustomerResponse.model_validate(row)

# ============================================================
# BLOQUE 7 - BUSCAR POR DOCUMENTO
# ============================================================
async def find_customer_by_document(
    session: AsyncSession, document_type: str, document_number: str
) -> CustomerResponse | None:
    result = await session.execute(
        _SELECT_BY_DOCUMENT_QUERY,
        {"document_type": document_type, "document_number": document_number},
    )
    row = result.mappings().first()
    if row is None:
        return None

    return CustomerResponse.model_validate(row)

# ============================================================
# BLOQUE 8 - BUSCAR POR NOMBRE
# ============================================================
async def find_customers_by_name(
    session: AsyncSession, query: str, limit: int = 20
) -> list[CustomerResponse]:
    pattern = f"%{query}%"
    result = await session.execute(
        _SELECT_BY_NAME_QUERY, {"pattern": pattern, "limit": limit}
    )
    rows = result.mappings().all()
    return [CustomerResponse.model_validate(row) for row in rows]

# ============================================================
# BLOQUE 9 - ACTUALIZAR CLIENTE
# ============================================================
async def update_customer(
    session: AsyncSession, customer_id: UUID, data: CustomerUpdate
) -> CustomerResponse:
    result = await session.execute(
        _UPDATE_QUERY,
        {
            "customer_id": customer_id,
            "full_name": data.full_name,
            "phone": data.phone,
            "address": data.address,
            "status": data.status,
            "notes": data.notes,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise CustomerNotFoundError()

    await session.commit()

    return CustomerResponse.model_validate(row)