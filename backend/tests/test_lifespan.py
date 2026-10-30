# ============================================================
# BLOQUE 1 - IMPORTACIONES
# Los mocks reemplazan configuracion y motor para no usar
# credenciales ni conexiones reales durante la prueba.
# ============================================================
from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

# ============================================================
# BLOQUE 2 - MODULO DE LA APLICACION
# Se importa el modulo para reemplazar exactamente las
# referencias que utiliza la funcion lifespan.
# ============================================================
main_module = import_module("app.main")


# ============================================================
# BLOQUE 3 - PRUEBA DEL CICLO DE VIDA
# Comprueba validacion inicial, liberacion al apagar y limpieza
# de caches. El motor falso nunca establece conexiones reales.
# ============================================================
def test_lifespan_initializes_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_settings_getter = Mock()
    fake_engine = Mock()
    fake_engine.dispose = AsyncMock()
    fake_engine_getter = Mock(return_value=fake_engine)
    fake_sessionmaker_getter = Mock()

    monkeypatch.setattr(main_module, "get_settings", fake_settings_getter)
    monkeypatch.setattr(main_module, "get_engine", fake_engine_getter)
    monkeypatch.setattr(
        main_module,
        "get_sessionmaker",
        fake_sessionmaker_getter,
    )

    with TestClient(main_module.app) as client:
        fake_settings_getter.assert_called_once_with()
        fake_engine_getter.assert_called_once_with()
        fake_engine.dispose.assert_not_awaited()

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    fake_engine.dispose.assert_awaited_once_with()
    fake_sessionmaker_getter.cache_clear.assert_called_once_with()
    fake_engine_getter.cache_clear.assert_called_once_with()
    fake_settings_getter.cache_clear.assert_called_once_with()