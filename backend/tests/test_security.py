# ============================================================
# BLOQUE 1 - IMPORTACIONES
# ============================================================
import logging
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import PyJWKClientConnectionError, PyJWKClientError

from app.core.config import Settings
from app.core.security import (
    AuthTokenInvalidError,
    KeysUnavailableError,
    verify_access_token,
)

# ============================================================
# BLOQUE 2 - CONFIGURACION Y CLAVES FICTICIAS
# Todo es de prueba: ningun secreto real, ninguna red.
# ============================================================
SUPABASE_URL = "https://proyecto-prueba.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
SUBJECT = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://usuario:clave@localhost/db",
        supabase_url=SUPABASE_URL,
    )


@pytest.fixture(scope="module")
def private_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="module")
def other_private_key():
    return ec.generate_private_key(ec.SECP256R1())


# ============================================================
# BLOQUE 3 - CLIENTE JWKS FALSO
# Imita a PyJWKClient: entrega una clave publica fija o lanza
# el error indicado.
# ============================================================
class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJWKClient:
    def __init__(self, public_key=None, error=None):
        self._public_key = public_key
        self._error = error

    def get_signing_key_from_jwt(self, token):
        if self._error is not None:
            raise self._error
        return FakeSigningKey(self._public_key)


@pytest.fixture
def jwks_client(private_key) -> FakeJWKClient:
    return FakeJWKClient(public_key=private_key.public_key())


# ============================================================
# BLOQUE 4 - FABRICA DE TOKENS
# ============================================================
def make_token(key, *, algorithm="ES256", remove=(), **overrides) -> str:
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "aud": "authenticated",
        "sub": SUBJECT,
        "iat": now,
        "exp": now + 3600,
    }
    payload.update(overrides)
    for claim in remove:
        payload.pop(claim, None)
    return jwt.encode(payload, key, algorithm=algorithm, headers={"kid": "k1"})


# ============================================================
# BLOQUE 5 - CASOS VALIDOS
# ============================================================
def test_valid_token_returns_claims(settings, private_key, jwks_client):
    token = make_token(private_key)
    claims = verify_access_token(token, settings=settings, jwks_client=jwks_client)
    assert claims["sub"] == SUBJECT
    assert claims["aud"] == "authenticated"


# ============================================================
# BLOQUE 6 - TOKENS INVALIDOS
# ============================================================
def test_expired_token_is_rejected(settings, private_key, jwks_client):
    token = make_token(private_key, exp=int(time.time()) - 3600)
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


def test_token_signed_with_other_key_is_rejected(
    settings, other_private_key, jwks_client
):
    token = make_token(other_private_key)
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


def test_wrong_issuer_is_rejected(settings, private_key, jwks_client):
    token = make_token(private_key, iss="https://otro-proyecto.supabase.co/auth/v1")
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


def test_wrong_audience_is_rejected(settings, private_key, jwks_client):
    token = make_token(private_key, aud="anon")
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


@pytest.mark.parametrize("claim", ["exp", "iss", "aud", "sub"])
def test_missing_required_claim_is_rejected(
    settings, private_key, jwks_client, claim
):
    token = make_token(private_key, remove=(claim,))
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


def test_empty_subject_is_rejected(settings, private_key, jwks_client):
    token = make_token(private_key, sub="   ")
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


def test_hs256_token_is_rejected(settings, jwks_client):
    secreto = "secreto-de-prueba-con-mas-de-32-caracteres!!"
    token = make_token(secreto, algorithm="HS256")
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


@pytest.mark.parametrize("token", ["", "   ", "no-es-un-jwt"])
def test_empty_or_garbage_token_is_rejected(settings, jwks_client, token):
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)


# ============================================================
# BLOQUE 7 - FALLOS AL OBTENER CLAVES
# Conexion caida -> KeysUnavailableError (503).
# kid desconocido -> token invalido (401).
# ============================================================
def test_jwks_connection_failure_is_distinguished(settings, private_key):
    client = FakeJWKClient(error=PyJWKClientConnectionError("sin red"))
    token = make_token(private_key)
    with pytest.raises(KeysUnavailableError):
        verify_access_token(token, settings=settings, jwks_client=client)


def test_unknown_kid_is_invalid_token(settings, private_key):
    client = FakeJWKClient(error=PyJWKClientError("kid desconocido"))
    token = make_token(private_key)
    with pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=client)


# ============================================================
# BLOQUE 8 - NO FILTRAR EL TOKEN EN LOS LOGS
# ============================================================
def test_rejected_token_is_not_logged(
    settings, other_private_key, jwks_client, caplog
):
    token = make_token(other_private_key)
    with caplog.at_level(logging.DEBUG), pytest.raises(AuthTokenInvalidError):
        verify_access_token(token, settings=settings, jwks_client=jwks_client)
    assert token not in caplog.text