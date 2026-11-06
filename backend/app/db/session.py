# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


# ============================================================
# BLOQUE 2 - MOTOR DE CONEXION
# Se crea una sola vez, la primera vez que se necesita (no al
# importar). Se usa NullPool porque el pooling lo maneja el
# Transaction Pooler de Supabase. Se desactivan los prepared
# statements porque el pooler en modo transaccion no los
# soporta y provocan DBAPIError.
# ============================================================
@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url.get_secret_value(),
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )



# ============================================================
# BLOQUE 3 - FABRICA DE SESIONES
# expire_on_commit=False evita recargar objetos tras confirmar
# una transaccion, comportamiento habitual en APIs async.
# ============================================================
@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)



# ============================================================
# BLOQUE 4 - DEPENDENCIA PARA FASTAPI
# Entrega una sesion por peticion y la cierra al terminar.
# Los endpoints la reciben con Depends(get_session).
# ============================================================
async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session