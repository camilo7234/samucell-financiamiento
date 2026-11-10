# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from enum import StrEnum


# ============================================================
# BLOQUE 2 - ROLES VALIDOS
# Deben coincidir exactamente con el CHECK de profiles.role en
# la migracion core_security: 'admin' y 'operator'.
# ============================================================
class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"


# ============================================================
# BLOQUE 3 - MENSAJE UNICO DE 403
# Mismo texto para: sin perfil, perfil inactivo, rol invalido y
# rol insuficiente. La causa real solo va al log del servidor.
# ============================================================
FORBIDDEN_DETAIL = "Acceso denegado"


# ============================================================
# BLOQUE 4 - CONVERSION ESTRICTA DE ROL
# Devuelve None si el valor no es un rol valido. Es sensible a
# mayusculas y espacios, igual que el CHECK de la base de datos.
# ============================================================
def parse_role(value: object) -> Role | None:
    if not isinstance(value, str):
        return None
    try:
        return Role(value)
    except ValueError:
        return None