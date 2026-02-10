"""
Cryptographic utilities for encrypting sensitive data.

Uses Fernet symmetric encryption with key derived from SECRET_KEY.
"""
import base64
import hashlib
import json
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from app.lib.config import settings


def _get_fernet_key() -> bytes:
    """
    Derive a Fernet-compatible key from the application SECRET_KEY.

    Fernet requires a 32-byte key, base64-encoded.
    We use SHA-256 to derive a consistent 32-byte key from any secret.
    """
    # Hash the secret to get exactly 32 bytes
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    # Base64 encode for Fernet
    return base64.urlsafe_b64encode(key_bytes)


def get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    return Fernet(_get_fernet_key())


def encrypt_credentials(credentials: Dict[str, Any]) -> str:
    """
    Encrypt a credentials dictionary.

    Args:
        credentials: Dictionary of credential key-value pairs

    Returns:
        Base64-encoded encrypted string
    """
    if not credentials:
        return ""

    fernet = get_fernet()
    json_bytes = json.dumps(credentials).encode('utf-8')
    encrypted = fernet.encrypt(json_bytes)
    return encrypted.decode('utf-8')


def decrypt_credentials(encrypted: str) -> Optional[Dict[str, Any]]:
    """
    Decrypt an encrypted credentials string.

    Args:
        encrypted: Base64-encoded encrypted string

    Returns:
        Decrypted credentials dictionary, or None if decryption fails
    """
    if not encrypted:
        return None

    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted.encode('utf-8'))
        return json.loads(decrypted.decode('utf-8'))
    except (InvalidToken, json.JSONDecodeError):
        return None


def has_credentials(encrypted: Optional[str]) -> bool:
    """Check if encrypted credentials exist and are valid."""
    if not encrypted:
        return False
    return decrypt_credentials(encrypted) is not None
