# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credit_calculator import (
    CreditCalculationError,
    calculate_credit_plan,
)
from app.modules.credits.schemas import CreditCreate, CreditResponse


# ============================================================
# BLOQUE 2 - ERRORES DE NEGOCIO
# ============================================================
class StoreNotFoundError(Exception):
    pass


class CustomerNotFoundError(Exception):
    pass


class InventoryItemNotFoundError(Exception):
    pass


class InventoryItemNotAvailableError(Exception):
    pass


class CreditConfigurationError(Exception):
    pass


class CreditNotFoundError(Exception):
    pass

# ============================================================
# BLOQUE 3 - CONSULTAS PARAMETRIZADAS
# ============================================================
_SELECT_ACTIVE_STORE_QUERY = text(
    "SELECT id "
    "FROM public.stores "
    "WHERE id = :store_id AND is_active = true"
)

_SELECT_ACTIVE_CUSTOMER_QUERY = text(
    "SELECT id "
    "FROM public.customers "
    "WHERE id = :customer_id AND status = 'active'"
)

_SELECT_AVAILABLE_INVENTORY_ITEM_QUERY = text(
    "SELECT id, sale_price_amount "
    "FROM public.inventory_items "
    "WHERE id = :inventory_item_id "
    "AND store_id = :store_id "
    "AND status = 'available' "
    "FOR UPDATE"
)

_SELECT_USURY_RATE_QUERY = text(
    "SELECT value "
    "FROM public.system_settings "
    "WHERE key = 'credit.usury_rate_ea'"
)

_INSERT_SALE_QUERY = text(
    "INSERT INTO public.sales "
    "(store_id, customer_id, sale_type, sale_status, subtotal_amount, "
    "discount_amount, total_amount, payment_status, sold_at, confirmed_at, "
    "confirmed_by) "
    "VALUES ("
    ":store_id, :customer_id, 'credit', 'confirmed', :subtotal_amount, "
    "0, :total_amount, 'pending', now(), now(), :confirmed_by) "
    "RETURNING id, sale_number"
)

_INSERT_SALE_ITEM_QUERY = text(
    "INSERT INTO public.sale_items "
    "(sale_id, sale_status, inventory_item_id, description_snapshot, "
    "unit_price_amount, quantity, total_amount) "
    "VALUES ("
    ":sale_id, 'confirmed', :inventory_item_id, :description_snapshot, "
    ":unit_price_amount, 1, :total_amount)"
)

_RESERVE_INVENTORY_ITEM_QUERY = text(
    "UPDATE public.inventory_items "
    "SET status = 'reserved' "
    "WHERE id = :inventory_item_id"
)

_INSERT_INVENTORY_MOVEMENT_QUERY = text(
    "INSERT INTO public.inventory_movements "
    "(store_id, inventory_item_id, movement_type, from_status, to_status, "
    "reference_type, reference_id, performed_by, notes) "
    "VALUES ("
    ":store_id, :inventory_item_id, 'reserve', 'available', 'reserved', "
    "'sale', :sale_id, :performed_by, :notes)"
)

_INSERT_CREDIT_PLAN_QUERY = text(
    "INSERT INTO public.credit_plans "
    "(store_id, sale_id, initial_percentage, initial_amount, financed_amount, "
    "nominal_rate, effective_annual_rate, interest_amount, "
    "total_obligation_amount, installment_count, installment_amount, "
    "frequency, purchased_date, first_due_date, rounding_rule, "
    "due_date_policy, liquidation_method, status, calculation_version) "
    "VALUES ("
    ":store_id, :sale_id, :initial_percentage, :initial_amount, "
    ":financed_amount, :nominal_rate, :effective_annual_rate, "
    ":interest_amount, :total_obligation_amount, :installment_count, "
    ":installment_amount, 'monthly', CURRENT_DATE, :first_due_date, "
    "'ceil_last_installment', 'last_day_of_month', "
    "'fixed_interest_on_financed', 'active', 'v1') "
    "RETURNING id"
)

_INSERT_INSTALLMENT_QUERY = text(
    "INSERT INTO public.installments "
    "(credit_plan_id, installment_number, due_date, principal_amount, "
    "interest_amount, total_amount, paid_amount, status) "
    "VALUES ("
    ":credit_plan_id, :installment_number, :due_date, :principal_amount, "
    ":interest_amount, :total_amount, 0, 'pending')"
)

_SELECT_CREDIT_RESPONSE_QUERY = text(
    "SELECT "
    "cp.id, "
    "cp.sale_id, "
    "cp.store_id, "
    "sa.customer_id, "
    "si.inventory_item_id, "
    "sa.sale_number, "
    "sa.total_amount AS sale_total_amount, "
    "cp.initial_amount, "
    "cp.financed_amount, "
    "cp.nominal_rate, "
    "cp.effective_annual_rate, "
    "cp.interest_amount, "
    "cp.total_obligation_amount, "
    "cp.installment_count, "
    "cp.installment_amount, "
    "cp.first_due_date, "
    "cp.status, "
    "sa.notes, "
    "cp.created_at, "
    "cp.updated_at "
    "FROM public.credit_plans cp "
    "JOIN public.sales sa ON sa.id = cp.sale_id "
    "JOIN public.sale_items si ON si.sale_id = sa.id "
    "WHERE cp.id = :credit_plan_id"
)

_SELECT_INSTALLMENTS_QUERY = text(
    "SELECT "
    "id, "
    "credit_plan_id, "
    "installment_number, "
    "due_date, "
    "principal_amount, "
    "interest_amount, "
    "total_amount, "
    "paid_amount, "
    "status, "
    "paid_at "
    "FROM public.installments "
    "WHERE credit_plan_id = :credit_plan_id "
    "ORDER BY installment_number"
)


# ============================================================
# BLOQUE 4 - UTILIDADES PRIVADAS
# ============================================================
def _parse_usury_rate(value: object) -> Decimal:
    # El valor se almacena en JSONB; debe poder convertirse a Decimal.
    if value is None:
        raise CreditConfigurationError()

    try:
        usury_rate = Decimal(str(value))
    except Exception as exc:
        raise CreditConfigurationError() from exc

    if usury_rate <= 0:
        raise CreditConfigurationError()

    return usury_rate


def _calculate_due_dates(
    first_due_date: date, installment_count: int
) -> list[date]:
    # Genera vencimientos mensuales conservando el dia solicitado.
    due_dates: list[date] = []
    current_year = first_due_date.year
    current_month = first_due_date.month
    requested_day = first_due_date.day

    for _ in range(installment_count):
        due_dates.append(date(current_year, current_month, requested_day))

        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1

    return due_dates


# ============================================================
# BLOQUE 5 - CREACION TRANSACCIONAL DE CREDITO
# ============================================================
async def create_credit(
    session: AsyncSession,
    data: CreditCreate,
    current_user_id: UUID,
) -> CreditResponse:
    # 5.1) Validar sucursal activa
    store_result = await session.execute(
        _SELECT_ACTIVE_STORE_QUERY,
        {"store_id": data.store_id},
    )
    if store_result.mappings().first() is None:
        raise StoreNotFoundError()

    # 5.2) Validar cliente activo
    customer_result = await session.execute(
        _SELECT_ACTIVE_CUSTOMER_QUERY,
        {"customer_id": data.customer_id},
    )
    if customer_result.mappings().first() is None:
        raise CustomerNotFoundError()

    # 5.3) Validar y bloquear el equipo disponible
    inventory_result = await session.execute(
        _SELECT_AVAILABLE_INVENTORY_ITEM_QUERY,
        {
            "inventory_item_id": data.inventory_item_id,
            "store_id": data.store_id,
        },
    )
    inventory_item = inventory_result.mappings().first()
    if inventory_item is None:
        raise InventoryItemNotFoundError()

    sale_total_amount = inventory_item["sale_price_amount"]

    # 5.4) Leer el tope de usura configurado
    usury_result = await session.execute(_SELECT_USURY_RATE_QUERY)
    usury_row = usury_result.mappings().first()
    if usury_row is None:
        raise CreditConfigurationError()

    usury_rate_ea = _parse_usury_rate(usury_row["value"])

    # 5.5) Calcular el plan financiero y validar usura
    try:
        calculation = calculate_credit_plan(
            sale_total_amount=sale_total_amount,
            initial_percentage=data.initial_percentage,
            nominal_rate=data.nominal_rate,
            installment_count=data.installment_count,
            usury_rate_ea=usury_rate_ea,
        )
    except CreditCalculationError as exc:
        raise CreditConfigurationError() from exc

    # 5.6) Crear la venta confirmada
    sale_result = await session.execute(
        _INSERT_SALE_QUERY,
        {
            "store_id": data.store_id,
            "customer_id": data.customer_id,
            "subtotal_amount": sale_total_amount,
            "total_amount": sale_total_amount,
            "confirmed_by": current_user_id,
        },
    )
    sale = sale_result.mappings().first()
    if sale is None:
        raise SQLAlchemyError("No se pudo crear la venta")

    sale_id = sale["id"]

    # 5.7) Crear el item de venta
    await session.execute(
        _INSERT_SALE_ITEM_QUERY,
        {
            "sale_id": sale_id,
            "inventory_item_id": data.inventory_item_id,
            "description_snapshot": "Equipo financiado",
            "unit_price_amount": sale_total_amount,
            "total_amount": sale_total_amount,
        },
    )

    # 5.8) Reservar el equipo y registrar el movimiento
    await session.execute(
        _RESERVE_INVENTORY_ITEM_QUERY,
        {"inventory_item_id": data.inventory_item_id},
    )

    await session.execute(
        _INSERT_INVENTORY_MOVEMENT_QUERY,
        {
            "store_id": data.store_id,
            "inventory_item_id": data.inventory_item_id,
            "sale_id": sale_id,
            "performed_by": current_user_id,
            "notes": data.notes,
        },
    )

    # 5.9) Crear el plan de credito
    credit_plan_result = await session.execute(
        _INSERT_CREDIT_PLAN_QUERY,
        {
            "store_id": data.store_id,
            "sale_id": sale_id,
            "initial_percentage": data.initial_percentage,
            "initial_amount": sale_total_amount - calculation.financed_amount,
            "financed_amount": calculation.financed_amount,
            "nominal_rate": calculation.nominal_rate,
            "effective_annual_rate": calculation.effective_annual_rate,
            "interest_amount": calculation.interest_amount,
            "total_obligation_amount": calculation.total_obligation_amount,
            "installment_count": calculation.installment_count,
            "installment_amount": calculation.installment_amount,
            "first_due_date": data.first_due_date,
        },
    )
    credit_plan = credit_plan_result.mappings().first()
    if credit_plan is None:
        raise SQLAlchemyError("No se pudo crear el plan de credito")

    credit_plan_id = credit_plan["id"]

    # 5.10) Crear todas las cuotas
    due_dates = _calculate_due_dates(
        data.first_due_date,
        calculation.installment_count,
    )

    for installment_number in range(calculation.installment_count):
        await session.execute(
            _INSERT_INSTALLMENT_QUERY,
            {
                "credit_plan_id": credit_plan_id,
                "installment_number": installment_number + 1,
                "due_date": due_dates[installment_number],
                "principal_amount": calculation.principal_amounts[
                    installment_number
                ],
                "interest_amount": calculation.interest_amounts[
                    installment_number
                ],
                "total_amount": calculation.total_amounts[installment_number],
            },
        )

    # 5.11) Confirmar la transaccion completa
    await session.commit()

    # 5.12) Consultar el credito creado con sus cuotas
    return await get_credit(session, credit_plan_id)


# ============================================================
# BLOQUE 6 - CONSULTAR CREDITO POR ID
# ============================================================
async def get_credit(
    session: AsyncSession, credit_plan_id: UUID
) -> CreditResponse:
    credit_result = await session.execute(
        _SELECT_CREDIT_RESPONSE_QUERY,
        {"credit_plan_id": credit_plan_id},
    )
    credit_row = credit_result.mappings().first()
    if credit_row is None:
        raise CreditNotFoundError()

    installments_result = await session.execute(
        _SELECT_INSTALLMENTS_QUERY,
        {"credit_plan_id": credit_plan_id},
    )
    installment_rows = installments_result.mappings().all()

    return CreditResponse.model_validate(
        {
            **credit_row,
            "installments": installment_rows,
        }
    )