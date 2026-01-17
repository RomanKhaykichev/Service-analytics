from uuid import UUID
from fastapi import Request, HTTPException
from typing import Optional
import os


def get_user_id(request: Request) -> str:
    """
    Extract and validate user_id from X-User-Id header.
    For local development, can use default user_id from env or skip auth.
    """
    user_id_str = request.headers.get("X-User-Id")
    
    # For local development: allow default user_id from env
    if not user_id_str:
        default_user_id = os.getenv("DEFAULT_USER_ID")
        if default_user_id:
            try:
                UUID(default_user_id)
                return default_user_id
            except ValueError:
                pass
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    
    try:
        # Validate UUID format
        UUID(user_id_str)
        return user_id_str
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id format (must be UUID)")
