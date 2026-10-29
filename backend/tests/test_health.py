# ============================================================
# BLOQUE 1 - IMPORTACIONES
# TestClient simula peticiones HTTP contra la app sin levantar
# un servidor real ni abrir puertos.
# ============================================================
from fastapi.testclient import TestClient

from app.main import app

# ============================================================
# BLOQUE 2 - CLIENTE DE PRUEBA
# Se crea una sola vez y se reutiliza en las pruebas del archivo.
# ============================================================
client = TestClient(app)


# ============================================================
# BLOQUE 3 - PRUEBA DEL ENDPOINT /health
# Verifica el codigo HTTP 200 y el cuerpo exacto de la respuesta.
# Si alguien cambia el endpoint por error, esta prueba falla.
# ============================================================
def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}