# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================
# BLOQUE 2 - PERFIL (DATO CRUDO DE LA BASE DE DATOS)
# role se conserva como texto: la validacion del rol y del estado
# activo se hace en la dependencia get_current_profile.
# ============================================================
@dataclass(frozen=True, slots=True)
class Profile:
    user_id: UUID
    full_name: str
    role: str
    is_active: bool


# ============================================================
# BLOQUE 3 - CONSULTA PARAMETRIZADA
# Solo lectura sobre public.profiles. El user_id viaja como
# parametro, nunca dentro del texto SQL.
# ============================================================
_PROFILE_QUERY = text(
    "SELECT id, full_name, role, is_active "
    "FROM public.profiles "
    "WHERE id = :user_id"
)


# ============================================================
# BLOQUE 4 - BUSQUEDA DE PERFIL
# Devuelve None si el usuario autenticado no tiene perfil.
# No cachea: se consulta en cada peticion.
# ============================================================
async def fetch_profile(session: AsyncSession, user_id: UUID) -> Profile | None:
    result = await session.execute(_PROFILE_QUERY, {"user_id": user_id})
    row = result.mappings().first()
    if row is None:
        return None
    return Profile(
        user_id=row["id"],
        full_name=row["full_name"],
        role=row["role"],
        is_active=row["is_active"],
    )