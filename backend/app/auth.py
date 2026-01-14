from uuid import UUID
from fastapi import Request, HTTPException


def get_user_id(request: Request) -> str:
    """Extract and validate user_id from X-User-Id header."""
    user_id_str = request.headers.get("X-User-Id")
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    
    try:
        # Validate UUID format
        UUID(user_id_str)
        return user_id_str
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id format (must be UUID)")
