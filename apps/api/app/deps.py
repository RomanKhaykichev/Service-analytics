from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
import logging
from app.settings import get_settings
from app.auth.jwt import decode_token
from jose import JWTError

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Unified dependency to get user_id from either:
    1. JWT Bearer token (Authorization: Bearer <token>) - preferred
    2. X-User-Id header (dev fallback)
    
    Returns:
        UUID: Validated user_id as UUID object
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Try JWT Bearer token first
    if credentials:
        try:
            token = credentials.credentials
            payload = decode_token(token)
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )
            
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            
            try:
                return UUID(user_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid user_id in token"
                )
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            # Fall through to X-User-Id check
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"JWT processing error: {e}")
            # Fall through to X-User-Id check
    
    # Fallback to X-User-Id header (dev mode)
    user_id_str = request.headers.get("X-User-Id")
    
    if not user_id_str:
        if settings.APP_ENV.lower() in ("dev", "development"):
            default_user_id = settings.DEFAULT_DEV_USER_ID
            logger.info(f"Dev mode: using default user_id {default_user_id} (no auth provided)")
            try:
                return UUID(default_user_id)
            except ValueError:
                logger.error(f"Invalid DEFAULT_DEV_USER_ID format: {default_user_id}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid DEFAULT_DEV_USER_ID configuration: {default_user_id}"
                )
        else:
            logger.warning("Missing authentication (production mode)")
            raise HTTPException(
                status_code=401,
                detail="Missing authentication"
            )
    
    # Validate UUID format
    try:
        return UUID(user_id_str)
    except ValueError:
        logger.warning(f"Invalid X-User-Id format: {user_id_str}")
        raise HTTPException(
            status_code=401,
            detail="Invalid X-User-Id format (must be UUID)"
        )


def require_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Legacy dependency for X-User-Id header only.
    Deprecated: use require_user() instead.
    
    This function is kept for backward compatibility but should not be used in new code.
    Use `user_id: UUID = Depends(require_user)` instead.
    """
    # Delegate to require_user to maintain same behavior
    return require_user(request, credentials)
