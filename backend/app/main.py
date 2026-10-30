# ============================================================
# BLOQUE 1 - IMPORTACIONES
# Herramientas para el ciclo de vida, dependencias y consultas.
# ============================================================
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_engine, get_session, get_sessionmaker

# ============================================================
# BLOQUE 2 - CICLO DE VIDA Y CREACION DE LA APLICACION
# Al arrancar: valida la configuracion y prepara el motor.
# Crear el motor no abre por si solo una conexion a PostgreSQL.
# Al apagar: libera conexiones y limpia las fabricas cacheadas.
# ============================================================
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_settings()
    engine = get_engine()

    try:
        yield
    finally:
        try:
            await engine.dispose()
        finally:
            get_sessionmaker.cache_clear()
            get_engine.cache_clear()
            get_settings.cache_clear()


app = FastAPI(
    title="Samucell Financiamiento API",
    version="0.1.0",
    lifespan=lifespan,
)

# ============================================================
# BLOQUE 3 - SALUD DEL SERVIDOR
# Comprueba que la API responde, sin consultar PostgreSQL.
# ============================================================
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ============================================================
# BLOQUE 4 - SALUD DE LA BASE DE DATOS
# Recibe una sesion mediante inyeccion de dependencias.
# Captura errores de SQLAlchemy, red y tiempo de espera.
# Los errores de programacion no se ocultan como fallos de BD.
# ============================================================
@app.get("/health/db")
async def health_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    try:
        await session.execute(text("select 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        logger.error("Fallo en /health/db: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible",
        ) from None

    return {"status": "ok", "database": "connected"}