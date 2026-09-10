"""
Token encryption at rest (Phase 9.7) — platform_connections.access_token_encrypted.

Fernet (AES-128-CBC + HMAC) with a key DERIVED from the application SECRET_KEY
(SHA-256 → urlsafe-b64). Rotating SECRET_KEY invalidates stored tokens —
documented in SOP_03: re-connect platforms after a secret rotation.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.core.logger import logger


def _fernet() -> Fernet:
    from src.config import settings
    key = hashlib.sha256((settings.SECRET_KEY or "").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(plaintext: str) -> str:
    """Encrypts a platform access token for storage. Never logs the value."""
    if not plaintext:
        raise ValueError("cannot encrypt empty token")
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypts a stored token. Raises ValueError on tampering/rotation."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        logger.error("Token decryption failed (secret rotated or tampered data)")
        raise ValueError("token decryption failed") from e
