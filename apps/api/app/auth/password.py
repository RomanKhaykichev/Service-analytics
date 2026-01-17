"""
Password hashing and verification using argon2.
"""
import argon2
from app.settings import get_settings

settings = get_settings()

# Argon2 password hasher
_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        _hasher.verify(password_hash, password)
        return True
    except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
        return False
