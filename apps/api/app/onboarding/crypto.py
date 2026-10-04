"""Credential encryption and signed OAuth state.

Credentials are stored as Fernet ciphertext (connector_credentials.secret_ciphertext).
Keys come from CONNECTOR_ENCRYPTION_KEYS (comma-separated, newest first) so they can be rotated.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class CryptoConfigError(RuntimeError):
    pass


class CredentialCipher:
    def __init__(self, keys: str):
        parts = [k.strip() for k in keys.split(",") if k.strip()]
        if not parts:
            raise CryptoConfigError("CONNECTOR_ENCRYPTION_KEYS is not configured")
        try:
            self._fernet = MultiFernet([Fernet(k.encode()) for k in parts])
        except ValueError as exc:
            raise CryptoConfigError("CONNECTOR_ENCRYPTION_KEYS contains an invalid Fernet key") from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise CryptoConfigError("Credential cannot be decrypted with the configured keys") from exc


class StateError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_state(secret: str, *, business_id: str, user_id: str, provider: str, ttl: int = 600) -> tuple[str, str, int]:
    """Return (token, nonce, expires_at). The nonce is also stored server-side to make the token single-use."""
    if not secret:
        raise CryptoConfigError("OAUTH_STATE_SECRET is not configured")
    nonce = secrets.token_urlsafe(24)
    exp = int(time.time()) + ttl
    body = _b64(json.dumps({"b": business_id, "u": user_id, "p": provider, "n": nonce, "e": exp}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", nonce, exp


def verify_state(secret: str, token: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise StateError("Malformed state") from exc
    expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        raise StateError("Invalid state signature")
    data = json.loads(_unb64(body))
    if data["e"] < time.time():
        raise StateError("State expired")
    return {"business_id": data["b"], "user_id": data["u"], "provider": data["p"], "nonce": data["n"]}
