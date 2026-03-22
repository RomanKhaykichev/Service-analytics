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


def _is_production_env() -> bool:
    """True when APP_ENV or ENV indicates production (X-User-Id must be disabled)."""
    if (settings.ENV or "").strip().lower() == "prod":
        return True
    return (settings.APP_ENV or "").strip().lower() == "prod"


def _allows_x_user_id_header() -> bool:
    """X-User-Id fallback is allowed only in dev/test-like environments."""
    if _is_production_env():
        return False
    env = (settings.APP_ENV or "").strip().lower()
    return env in ("dev", "development", "test")


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Unified dependency to get user_id from either:
    1. JWT Bearer token (Authorization: Bearer <token>) — required in production
    2. X-User-Id header — only when APP_ENV is dev/development/test (not prod)
    
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
            if _is_production_env():
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                ) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"JWT processing error: {e}")
            if _is_production_env():
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication",
                ) from e
    
    # Fallback to X-User-Id header (dev/test only)
    if not _allows_x_user_id_header():
        if request.headers.get("X-User-Id"):
            logger.warning("X-User-Id header is not allowed in this environment")
        raise HTTPException(
            status_code=401,
            detail="Missing authentication",
        )

    user_id_str = request.headers.get("X-User-Id")

    if not user_id_str:
        logger.warning("Missing authentication (no Authorization header and no X-User-Id)")
        raise HTTPException(
            status_code=401,
            detail="Missing authentication"
        )

    try:
        return UUID(user_id_str)
    except ValueError:
        logger.warning(f"Invalid X-User-Id format: {user_id_str}")
        raise HTTPException(
            status_code=401,
            detail="Invalid X-User-Id format (must be UUID)"
        )


def _admin_user_ids_set() -> set:
    """Parse ADMIN_USER_IDS (comma-separated emails or UUIDs) into a set of lowercase strings."""
    raw = (settings.ADMIN_USER_IDS or "").strip()
    if not raw:
        return set()
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def require_phone_verified(user_id: UUID, db) -> None:
    """
    Block non-admin users who have a phone on file but have not completed SMS verification.
    Users without a phone (legacy) are allowed.
    """
    if is_user_admin(user_id, db):
        return
    from sqlalchemy import text
    from app.db import qname
    row = db.execute(
        text(
            f"SELECT phone, phone_verified_at FROM {qname('users')} "
            "WHERE id = CAST(:uid AS uuid)"
        ),
        {"uid": str(user_id)},
    ).fetchone()
    if not row:
        return
    phone, pva = row[0], row[1]
    if phone and str(phone).strip() and pva is None:
        raise HTTPException(status_code=403, detail="Phone not verified")


def is_user_admin(user_id: UUID, db) -> bool:
    """Проверить, входит ли пользователь в ADMIN_USER_IDS (по id или email)."""
    admin_ids = _admin_user_ids_set()
    if not admin_ids:
        return False
    if str(user_id).lower() in admin_ids:
        return True
    from sqlalchemy import text
    from app.db import qname
    row = db.execute(
        text(f"SELECT email FROM {qname('users')} WHERE id = :uid"),
        {"uid": str(user_id)},
    ).fetchone()
    if row and row[0] and row[0].lower() in admin_ids:
        return True
    return False


def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Dependency for admin-only routes. Requires valid user (JWT or X-User-Id) and
    that the user is in ADMIN_USER_IDS (comma-separated emails or UUIDs in env).
    """
    user_id = require_user(request, credentials)
    admin_ids = _admin_user_ids_set()
    if not admin_ids:
        logger.warning("ADMIN_USER_IDS is empty; no one can access admin routes")
        raise HTTPException(status_code=403, detail="Admin access not configured")
    user_id_str = str(user_id).lower()
    if user_id_str in admin_ids:
        return user_id
    # Check by email (need DB)
    from app.db import SessionLocal
    from sqlalchemy import text
    from app.db import qname
    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {settings.DB_SCHEMA}, public"))
        row = db.execute(
            text(f"SELECT email FROM {qname('users')} WHERE id = :uid"),
            {"uid": str(user_id)},
        ).fetchone()
        if row and row[0]:
            if row[0].lower() in admin_ids:
                return user_id
    finally:
        db.close()
    raise HTTPException(status_code=403, detail="Admin access required")


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
