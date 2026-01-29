"""Encryption helpers for storing credentials."""

import base64
from cryptography.fernet import Fernet, InvalidToken

from ..config.settings import Config
from ..utils.logger import get_logger

logger = get_logger()


def _get_key() -> bytes:
    key = getattr(Config, "MT5_CRED_KEY", None)
    if not key:
        raise ValueError("MT5_CRED_KEY is not configured")
    if isinstance(key, str):
        return key.encode("utf-8")
    return key


def encrypt_text(value: str) -> str:
    fernet = Fernet(_get_key())
    token = fernet.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(value: str) -> str:
    fernet = Fernet(_get_key())
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Invalid credential token", exc_info=True)
        raise exc
