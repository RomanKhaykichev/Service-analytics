"""
JWT token creation and validation.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.settings import get_settings

settings = get_settings()


def create_access_token(user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User UUID as string
        additional_claims: Optional additional claims to include
        
    Returns:
        JWT token string
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TTL_MIN)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,  # subject (user_id)
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.JWT_ISSUER,
        "type": "access",
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User UUID as string
        
    Returns:
        JWT token string
    """
    expires_delta = timedelta(days=settings.REFRESH_TTL_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.JWT_ISSUER,
        "type": "refresh",
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            issuer=settings.JWT_ISSUER,
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")
