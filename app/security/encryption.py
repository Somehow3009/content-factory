import base64
import os

from cryptography.fernet import Fernet

from app.config.settings import settings


def _fernet() -> Fernet:
    key = settings.encryption_key.encode()
    if len(key) != 44:  # not a valid Fernet key -> derive deterministic dev key is FORBIDDEN; raise
        raise RuntimeError("ENCRYPTION_KEY must be a Fernet key (32 bytes base64). Generate with Fernet.generate_key().")
    return Fernet(key)


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()
