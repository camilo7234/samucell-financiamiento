# ============================================================
# BLOQUE 1 - IMPORTACIONES
# Annotated permite declarar dependencias sin llamadas en los
# valores por defecto de los argumentos.
# ============================================================
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

# ============================================================
# BLOQUE 2 - LOGGER Y APLICACION
# No se registran cadenas de conexion ni mensajes originales
# de excepciones que puedan contener informacion sensible.
# ============================================================
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Samucell Financiamiento API",
    version="0.1.0",
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