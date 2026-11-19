from decimal import Decimal

import pytest

from app.core.credit_calculator import (
    CreditCalculationError,
    calculate_credit_plan,
)


def test_calcula_credito_de_12_cuotas():
    result = calculate_credit_plan(
        sale_total_amount="1000000",
        initial_percentage="20",
        nominal_rate="3",
        installment_count=12,
        usury_rate_ea="50",
    )

    assert result.financed_amount == Decimal("800000.00")
    assert result.interest_amount == Decimal("288000.00")
    assert result.total_obligation_amount == Decimal("1088000.00")
    assert result.installment_amount == Decimal("90666.67")
    assert len(result.total_amounts) == 12
    assert sum(result.total_amounts) == result.total_obligation_amount
    assert sum(result.principal_amounts) == result.financed_amount
    assert sum(result.interest_amounts) == result.interest_amount


def test_ultima_cuota_absorbe_redondeo():
    result = calculate_credit_plan(
        sale_total_amount="1000",
        initial_percentage="0",
        nominal_rate="10",
        installment_count=3,
        usury_rate_ea="100",
    )

    assert result.financed_amount == Decimal("1000.00")
    assert result.interest_amount == Decimal("300.00")
    assert result.total_obligation_amount == Decimal("1300.00")
    assert result.installment_amount == Decimal("433.34")
    assert result.total_amounts[0] == Decimal("433.34")
    assert result.total_amounts[1] == Decimal("433.34")
    assert result.total_amounts[2] == Decimal("433.32")
    assert sum(result.total_amounts) == Decimal("1300.00")
    assert sum(result.principal_amounts) == Decimal("1000.00")
    assert sum(result.interest_amounts) == Decimal("300.00")


def test_calcula_tea_mensual():
    result = calculate_credit_plan(
        sale_total_amount="1000",
        initial_percentage="0",
        nominal_rate="3",
        installment_count=12,
        usury_rate_ea="50",
    )

    assert result.effective_annual_rate == Decimal("0.425761")


def test_rechaza_usura_null():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="3",
            installment_count=12,
            usury_rate_ea=None,
        )


def test_rechaza_usura_menor_a_tea():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="5",
            installment_count=12,
            usury_rate_ea="10",
        )


def test_rechaza_cuota_cero():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="3",
            installment_count=0,
            usury_rate_ea="50",
        )


def test_rechaza_cuota_mayor_a_60():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="3",
            installment_count=61,
            usury_rate_ea="50",
        )


def test_rechaza_cuota_booleana():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="3",
            installment_count=True,
            usury_rate_ea="50",
        )


def test_rechaza_tasa_negativa():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="0",
            nominal_rate="-1",
            installment_count=12,
            usury_rate_ea="50",
        )


def test_rechaza_inicial_igual_o_mayor_a_venta():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="100",
            nominal_rate="3",
            installment_count=12,
            usury_rate_ea="50",
        )


def test_rechaza_monto_venta_invalido():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="cero",
            initial_percentage="0",
            nominal_rate="3",
            installment_count=12,
            usury_rate_ea="50",
        )


def test_rechaza_porcentaje_inicial_negativo():
    with pytest.raises(CreditCalculationError):
        calculate_credit_plan(
            sale_total_amount="1000",
            initial_percentage="-1",
            nominal_rate="3",
            installment_count=12,
            usury_rate_ea="50",
        )