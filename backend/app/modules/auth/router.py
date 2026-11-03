# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.modules.auth.dependencies import AuthenticatedUser, get_current_user

# ============================================================
# BLOQUE 2 - ROUTER VERSIONADO
# ============================================================
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ============================================================
# BLOQUE 3 - RESPUESTA
# Solo lo imprescindible: nunca se devuelven los claims completos.
# ============================================================
class MeResponse(BaseModel):
    user_id: UUID


# ============================================================
# BLOQUE 4 - USUARIO AUTENTICADO ACTUAL
# Aun no consulta profiles: confirma que el token es valido.
# ============================================================
@router.get("/me", response_model=MeResponse)
def read_me(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> MeResponse:
    return MeResponse(user_id=user.user_id)