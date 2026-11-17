# ============================================================
# BLOQUE 1 - IMPORTACIONES
# Sin dependencias: la regla es pura y no accede a la base.
# ============================================================


# ============================================================
# BLOQUE 2 - EXCEPCION DE BLOQUEO NO ELEGIBLE
# La usara el futuro endpoint de bloqueo. Este archivo no
# decide el codigo HTTP ni el mensaje externo.
# ============================================================
class LockNotEligibleError(Exception):
    pass


# ============================================================
# BLOQUE 3 - VALIDACION ESTRICTA DE ENTEROS
# bool es subclase de int en Python: se rechaza de forma
# explicita para que True no cuente como 1 dia.
# ============================================================
def _is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ============================================================
# BLOQUE 4 - REGLA DE ELEGIBILIDAD
# days_overdue: dias de mora ya calculados por quien llama.
# min_days: umbral de collections.lock_eligibility_days,
# leido por quien llama; aqui no se fija ningun valor.
# Falla cerrada: dato invalido o umbral menor a 1 => False.
# Esta regla NO sustituye al interruptor global
# feature.device_lock_enabled ni a las demas condiciones
# de bloqueo (reserva, consentimientos, avisos, autorizacion).
# ============================================================
def is_lock_eligible(days_overdue: object, min_days: object) -> bool:
    if not _is_strict_int(days_overdue) or not _is_strict_int(min_days):
        return False
    if min_days < 1:
        return False
    return days_overdue >= min_days


# ============================================================
# BLOQUE 5 - EXIGENCIA DE ELEGIBILIDAD
# Para uso en el flujo de bloqueo: lanza LockNotEligibleError
# si la mora no alcanza el umbral. El mensaje no incluye
# valores ni datos del cliente.
# ============================================================
def ensure_lock_eligible(days_overdue: object, min_days: object) -> None:
    if not is_lock_eligible(days_overdue, min_days):
        raise LockNotEligibleError("Bloqueo no elegible")