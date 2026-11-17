# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import pytest

from app.core.lock_policy import (
    LockNotEligibleError,
    ensure_lock_eligible,
    is_lock_eligible,
)

# ============================================================
# BLOQUE 2 - UMBRAL DE PRUEBA
# Valor solo para las pruebas; el codigo de produccion no
# fija ningun umbral.
# ============================================================
TEST_MIN_DAYS = 15


# ============================================================
# BLOQUE 3 - LIMITE DEL UMBRAL
# Antes del umbral no es elegible; en el umbral y despues si.
# ============================================================
@pytest.mark.parametrize(
    ("days_overdue", "expected"),
    [
        (0, False),
        (1, False),
        (14, False),
        (15, True),
        (16, True),
        (45, True),
        (-1, False),
    ],
)
def test_eligibility_respects_threshold(days_overdue, expected):
    assert is_lock_eligible(days_overdue, TEST_MIN_DAYS) is expected


# ============================================================
# BLOQUE 4 - DIAS DE MORA INVALIDOS
# Falla cerrada: tipos no enteros o bool nunca son elegibles.
# ============================================================
@pytest.mark.parametrize(
    "days_overdue",
    [None, "15", "20", 15.0, 20.5, True, False, [], {}],
)
def test_invalid_days_overdue_is_never_eligible(days_overdue):
    assert is_lock_eligible(days_overdue, TEST_MIN_DAYS) is False


# ============================================================
# BLOQUE 5 - UMBRAL INVALIDO
# Un umbral ausente, no entero o menor a 1 no habilita nada,
# ni siquiera con una mora muy alta.
# ============================================================
@pytest.mark.parametrize(
    "min_days",
    [None, "15", 15.0, True, False, 0, -1, -15],
)
def test_invalid_threshold_is_never_eligible(min_days):
    assert is_lock_eligible(100, min_days) is False


# ============================================================
# BLOQUE 6 - EXIGENCIA DE ELEGIBILIDAD
# ensure_lock_eligible lanza la excepcion cuando no es elegible
# y no lanza nada cuando lo es.
# ============================================================
def test_ensure_raises_before_threshold():
    with pytest.raises(LockNotEligibleError):
        ensure_lock_eligible(14, TEST_MIN_DAYS)


def test_ensure_raises_with_invalid_threshold():
    with pytest.raises(LockNotEligibleError):
        ensure_lock_eligible(100, None)


def test_ensure_passes_at_and_after_threshold():
    assert ensure_lock_eligible(15, TEST_MIN_DAYS) is None
    assert ensure_lock_eligible(30, TEST_MIN_DAYS) is None


# ============================================================
# BLOQUE 7 - MENSAJE SIN DATOS
# El mensaje de la excepcion no expone valores ni datos.
# ============================================================
def test_error_message_is_generic():
    with pytest.raises(LockNotEligibleError) as exc_info:
        ensure_lock_eligible(3, TEST_MIN_DAYS)
    assert str(exc_info.value) == "Bloqueo no elegible"