# ==========================================================
# 1) IMPORTACIONES Y CONSTANTES
# ==========================================================
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Final

MIN_INSTALLMENT_COUNT: Final[int] = 1
MAX_INSTALLMENT_COUNT: Final[int] = 60
CENTS: Final[Decimal] = Decimal("0.01")
TEA_PRECISION: Final[Decimal] = Decimal("0.000001")


# ==========================================================
# 2) ERRORES DEL DOMINIO FINANCIERO
# ==========================================================
class CreditCalculationError(Exception):
    """Error de validacion o calculo de un plan de credito."""


# ==========================================================
# 3) RESULTADO DEL CALCULO
# ==========================================================
@dataclass(frozen=True)
class CreditCalculation:
    financed_amount: Decimal
    nominal_rate: Decimal
    installment_count: int
    interest_amount: Decimal
    total_obligation_amount: Decimal
    installment_amount: Decimal
    effective_annual_rate: Decimal
    principal_amounts: tuple[Decimal, ...]
    interest_amounts: tuple[Decimal, ...]
    total_amounts: tuple[Decimal, ...]


# ==========================================================
# 4) VALIDACIONES PRIVADAS
# ==========================================================
def _to_decimal(value: object) -> Decimal:
    # Convierte un valor de entrada a Decimal y rechaza tipos no numericos.
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise CreditCalculationError("Datos de credito invalidos")

    try:
        converted = Decimal(str(value))
    except Exception as exc:
        raise CreditCalculationError("Datos de credito invalidos") from exc

    if not converted.is_finite():
        raise CreditCalculationError("Datos de credito invalidos")

    return converted


def _validate_positive_amount(value: Decimal) -> None:
    # Un monto financiero relevante debe ser mayor que cero.
    if value <= 0:
        raise CreditCalculationError("Datos de credito invalidos")


# ==========================================================
# 5) CALCULO DEL PLAN DE CREDITO
# ==========================================================
def calculate_credit_plan(
    *,
    sale_total_amount: object,
    initial_percentage: object,
    nominal_rate: object,
    installment_count: object,
    usury_rate_ea: object,
) -> CreditCalculation:
    # 5.1) Conversion y validacion de entradas
    sale_total = _to_decimal(sale_total_amount)
    initial_percentage = _to_decimal(initial_percentage)
    nominal_rate = _to_decimal(nominal_rate)
    usury_rate = _to_decimal(usury_rate_ea)

    if not isinstance(installment_count, int) or isinstance(installment_count, bool):
        raise CreditCalculationError("Datos de credito invalidos")

    if not MIN_INSTALLMENT_COUNT <= installment_count <= MAX_INSTALLMENT_COUNT:
        raise CreditCalculationError("Datos de credito invalidos")

    _validate_positive_amount(sale_total)

    if not Decimal(0) <= initial_percentage < Decimal(100):
        raise CreditCalculationError("Datos de credito invalidos")

    if nominal_rate <= 0:
        raise CreditCalculationError("Datos de credito invalidos")

    if usury_rate <= 0:
        raise CreditCalculationError("Tope de usura no configurado")

    # 5.2) Calculo de inicial y monto financiado
    initial_amount = (
        sale_total * initial_percentage / Decimal(100)
    ).quantize(
        CENTS,
        rounding=ROUND_HALF_UP,
    )
    financed_amount = sale_total - initial_amount

    if financed_amount <= 0:
        raise CreditCalculationError("Datos de credito invalidos")

    # 5.3) Calculo de interes fijo sobre el monto financiado
    monthly_rate = nominal_rate / Decimal(100)
    interest_amount = (
        financed_amount * monthly_rate * installment_count
    ).quantize(
        CENTS,
        rounding=ROUND_HALF_UP,
    )
    total_obligation_amount = financed_amount + interest_amount

    # 5.4) Calculo de la cuota base con redondeo hacia arriba
    base_installment_amount = (
        total_obligation_amount / installment_count
    ).quantize(
        CENTS,
        rounding=ROUND_CEILING,
    )

    # 5.5) Calculo de la TEA efectiva para el plazo del credito
    effective_annual_rate = (
        (Decimal(1) + monthly_rate) ** installment_count - Decimal(1)
    ).quantize(
        TEA_PRECISION,
        rounding=ROUND_HALF_UP,
    )

    # 5.6) Validacion del tope de usura
    # usury_rate_ea se recibe como porcentaje: 10 equivale a 10%.
    usury_limit = usury_rate / Decimal(100)

    if effective_annual_rate > usury_limit:
        raise CreditCalculationError("Tope de usura excedido")

    # 5.7) Distribucion del total entre cuotas
    total_amounts: list[Decimal] = []
    accumulated_total = Decimal(0)

    for installment_number in range(1, installment_count + 1):
        if installment_number == installment_count:
            installment_total = total_obligation_amount - accumulated_total
        else:
            installment_total = base_installment_amount

        total_amounts.append(installment_total)
        accumulated_total += installment_total

    # 5.8) Distribucion del interes entre cuotas
    interest_per_installment = (
        interest_amount / installment_count
    ).quantize(
        CENTS,
        rounding=ROUND_HALF_UP,
    )

    interest_amounts: list[Decimal] = []
    accumulated_interest = Decimal(0)

    for installment_number in range(1, installment_count + 1):
        if installment_number == installment_count:
            installment_interest = interest_amount - accumulated_interest
        else:
            installment_interest = interest_per_installment

        interest_amounts.append(installment_interest)
        accumulated_interest += installment_interest

    # 5.9) Calculo del capital pagado en cada cuota
    principal_amounts = tuple(
        total_amounts[index] - interest_amounts[index]
        for index in range(installment_count)
    )

    # 5.10) Resultado inmutable listo para persistir
    return CreditCalculation(
        financed_amount=financed_amount,
        nominal_rate=nominal_rate,
        installment_count=installment_count,
        interest_amount=interest_amount,
        total_obligation_amount=total_obligation_amount,
        installment_amount=base_installment_amount,
        effective_annual_rate=effective_annual_rate,
        principal_amounts=principal_amounts,
        interest_amounts=tuple(interest_amounts),
        total_amounts=tuple(total_amounts),
    )