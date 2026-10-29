# ============================================================
# BLOQUE 1 - IMPORTACIONES
# FastAPI es el framework que expone la API HTTP.
# ============================================================
from fastapi import FastAPI

# ============================================================
# BLOQUE 2 - CREACION DE LA APLICACION
# "title" y "version" aparecen en la documentacion automatica
# (/docs). La version se actualizara al cerrar cada fase.
# ============================================================
app = FastAPI(
    title="Samucell Financiamiento API",
    version="0.1.0",
)


# ============================================================
# BLOQUE 3 - ENDPOINT DE SALUD
# GET /health confirma que el servidor esta vivo.
# No toca la base de datos ni devuelve datos sensibles.
# La verificacion de la base (/health/db) se agrega despues.
# ============================================================
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}