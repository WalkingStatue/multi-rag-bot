"""
Encryption utilities for API key management.
"""
from cryptography.fernet import Fernet
import base64
import hashlib
from ..core.config import settings


def _get_encryption_key() -> bytes:
    """
    Generate encryption key from secret key.
    
    Returns:
        Fernet encryption key
    """
    # Use the secret key to generate a consistent encryption key
    key_material = settings.secret_key.encode()
    # Hash to get consistent 32 bytes
    digest = hashlib.sha256(key_material).digest()
    # Encode to base64 for Fernet
    return base64.urlsafe_b64encode(digest)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key as string
    """
    fernet = Fernet(_get_encryption_key())
    encrypted_key = fernet.encrypt(api_key.encode())
    return encrypted_key.decode()


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Decrypt an API key for use.
    
    Args:
        encrypted_api_key: Encrypted API key string
        
    Returns:
        Decrypted API key
        
    Raises:
        Exception: If decryption fails
    """
    fernet = Fernet(_get_encryption_key())
    decrypted_key = fernet.decrypt(encrypted_api_key.encode())
    return decrypted_key.decode()