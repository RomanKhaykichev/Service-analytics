"""
Token hashing for refresh tokens (stored in database).
"""
import hashlib
import secrets


def hash_token(token: str) -> str:
    """
    Hash a refresh token for storage in database.
    Uses SHA-256 with a salt.
    
    Args:
        token: Plain refresh token
        
    Returns:
        Hashed token string
    """
    # Use SHA-256 for token hashing
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its hash.
    
    Args:
        token: Plain token
        token_hash: Hashed token from database
        
    Returns:
        True if token matches hash
    """
    computed_hash = hash_token(token)
    return secrets.compare_digest(computed_hash, token_hash)
