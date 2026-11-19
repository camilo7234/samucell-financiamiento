# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# BLOQUE 2 - ESQUEMA DE CREACION DE CREDITO
# ============================================================
class CreditCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: UUID
    customer_id: UUID
    inventory_item_id: UUID
    sale_total_amount: Decimal = Field(gt=0)
    initial_percentage: Decimal = Field(ge=0, lt=100)
    nominal_rate: Decimal = Field(gt=0)
    installment_count: int = Field(ge=1, le=60)
    first_due_date: date
    notes: str | None = Field(default=None, max_length=1000)


# ============================================================
# BLOQUE 3 - ESQUEMA DE CUOTA
# ============================================================
class InstallmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    credit_plan_id: UUID
    installment_number: int
    due_date: date
    principal_amount: Decimal
    interest_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    paid_at: datetime | None


# ============================================================
# BLOQUE 4 - ESQUEMA DE RESPUESTA DE CREDITO
# ============================================================
class CreditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sale_id: UUID
    store_id: UUID
    customer_id: UUID
    inventory_item_id: UUID
    sale_number: int
    sale_total_amount: Decimal
    initial_amount: Decimal
    financed_amount: Decimal
    nominal_rate: Decimal
    effective_annual_rate: Decimal
    interest_amount: Decimal
    total_obligation_amount: Decimal
    installment_count: int
    installment_amount: Decimal
    first_due_date: date
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    installments: list[InstallmentResponse]