from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from uuid import UUID
import logging
from app.db import get_db, qname
from app.settings import get_settings
from sqlalchemy import text

logger = logging.getLogger(__name__)
from app.deps import require_user, is_user_admin
from app.models import User, AuthIdentity, RefreshToken
from app.models.auth_identity import AuthProvider
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    UpdateProfileRequest,
    AuthResponse,
    TokenResponse,
    UserResponse,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_token_hash,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.
    """
    if not request.consent_processing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent to personal data processing is required"
        )
    try:
        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        if request.phone:
            existing_phone = db.query(User).filter(User.phone == request.phone).first()
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this phone number already exists"
                )

        # Check if auth identity with this email exists
        existing_identity = db.query(AuthIdentity).filter(
            and_(
                AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD,
                AuthIdentity.identifier == request.email
            )
        ).first()
        if existing_identity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Create user
        user = User(
            email=request.email,
            full_name=request.full_name or None,
            phone=request.phone or None,
            is_active=True
        )
        db.add(user)
        db.flush()  # Get user.id

        # Set initial trial period: 10 days from registration
        # Используем raw SQL, так как план/триал-колонки добавлены миграцией/ensure_auth_tables и не описаны в ORM-модели.
        try:
            now_utc = datetime.now(timezone.utc)
            trial_ends = now_utc + timedelta(days=10)
            db.execute(
                text(
                    f"UPDATE {qname('users')} "
                    "SET trial_ends_at = :end, plan = COALESCE(plan, 'trial') "
                    "WHERE id = :uid"
                ),
                {"end": trial_ends, "uid": user.id},
            )
        except Exception as e:
            logger.debug("trial_ends_at update skipped: %s", e)

        # Create auth identity (store provider as string for varchar column)
        password_hash = hash_password(request.password)
        auth_identity = AuthIdentity(
            user_id=user.id,
            provider=AuthProvider.EMAIL_PASSWORD,
            identifier=request.email,
            password_hash=password_hash
        )
        db.add(auth_identity)

        # Create tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Store refresh token hash
        refresh_token_hash = hash_token(refresh_token)
        from app.settings import get_settings
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TTL_DAYS)

        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at
        )
        db.add(db_refresh_token)

        db.commit()
        db.refresh(user)
        user_resp = UserResponse.model_validate(user)
        user_resp.is_admin = is_user_admin(user.id, db)
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_resp
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Registration failed")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Поиск по email без учёта регистра (identifier хранит текущий email пользователя).
    """
    email_lower = (request.email or "").strip().lower()
    if not email_lower:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
    auth_identity = db.query(AuthIdentity).filter(
        and_(
            AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD,
            func.lower(AuthIdentity.identifier) == email_lower
        )
    ).first()
    
    if not auth_identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not auth_identity.password_hash or not verify_password(request.password, auth_identity.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Get user
    user = db.query(User).filter(User.id == auth_identity.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )
    
    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    # Store refresh token hash
    refresh_token_hash = hash_token(refresh_token)
    from datetime import timedelta
    from app.settings import get_settings
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TTL_DAYS)
    
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    
    # Update last_login_at and записать посещение для графика «Посещения»
    now_utc = datetime.now(timezone.utc)
    try:
        db.execute(text(f"UPDATE {qname('users')} SET last_login_at = :now WHERE id = :uid"), {"now": now_utc, "uid": user.id})
    except Exception as e:
        logger.debug("last_login_at update skipped: %s", e)
    schema = get_settings().DB_SCHEMA
    r = db.execute(text("SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = 'login_events'"), {"s": schema}).fetchone()
    if r:
        try:
            db.execute(text(f"INSERT INTO {qname('login_events')} (user_id, logged_at) VALUES (:uid, :now)"), {"uid": user.id, "now": now_utc})
            logger.info("login_events: записано посещение user_id=%s", user.id)
        except Exception as e:
            logger.warning("login_events insert failed: %s", e)
    else:
        logger.warning("Таблица login_events отсутствует — метрика «Посещения» будет 0. Выполните: cd apps/api && alembic upgrade head")
    db.commit()
    db.refresh(user)
    user_resp = UserResponse.model_validate(user)
    user_resp.is_admin = is_user_admin(user.id, db)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Rotates refresh token (old one is revoked, new one is issued).
    """
    try:
        # Decode refresh token
        payload = decode_token(request.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user_id in token"
            )
        
        # Find refresh token in database
        refresh_token_hash = hash_token(request.refresh_token)
        db_refresh_token = db.query(RefreshToken).filter(
            and_(
                RefreshToken.token_hash == refresh_token_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        ).first()
        
        if not db_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Revoke old refresh token
        db_refresh_token.revoked_at = datetime.now(timezone.utc)
        
        # Create new tokens
        new_access_token = create_access_token(str(user_id))
        new_refresh_token = create_refresh_token(str(user_id))
        
        # Store new refresh token
        new_refresh_token_hash = hash_token(new_refresh_token)
        from datetime import timedelta
        from app.settings import get_settings
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TTL_DAYS)
        
        new_db_refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=new_refresh_token_hash,
            expires_at=expires_at
        )
        db.add(new_db_refresh_token)
        
        now_utc = datetime.now(timezone.utc)
        try:
            db.execute(text(f"UPDATE {qname('users')} SET last_login_at = :now WHERE id = :uid"), {"now": now_utc, "uid": user_id})
        except Exception as e:
            logger.debug("last_login_at update skipped: %s", e)
        schema = get_settings().DB_SCHEMA
        r = db.execute(text("SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = 'login_events'"), {"s": schema}).fetchone()
        if r:
            try:
                db.execute(text(f"INSERT INTO {qname('login_events')} (user_id, logged_at) VALUES (:uid, :now)"), {"uid": user_id, "now": now_utc})
                logger.info("login_events: записано посещение user_id=%s (refresh)", user_id)
            except Exception as e:
                logger.warning("login_events insert failed: %s", e)
        else:
            logger.warning("Таблица login_events отсутствует — выполните: alembic upgrade head")
        db.commit()
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking refresh token.
    """
    refresh_token_hash = hash_token(request.refresh_token)
    
    db_refresh_token = db.query(RefreshToken).filter(
        and_(
            RefreshToken.token_hash == refresh_token_hash,
            RefreshToken.revoked_at.is_(None)
        )
    ).first()
    
    if db_refresh_token:
        db_refresh_token.revoked_at = datetime.now(timezone.utc)
        db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user.
    Requires Bearer access token or X-User-Id header (dev mode).
    If user was deleted (e.g. dev@example.com), returns 404 — client should clear auth and redirect to login.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    resp = UserResponse.model_validate(user)
    resp.is_admin = is_user_admin(user_id, db)
    return resp


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile (full_name, email, phone).
    If email is changed, auth identity identifier is updated so login continues to work.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if request.full_name is not None:
        user.full_name = (request.full_name.strip() or None) if request.full_name else None
    
    if request.email is not None:
        new_email = (request.email.strip() or None) if request.email else None
        if new_email and new_email != (user.email or ""):
            existing = db.query(User).filter(User.email == new_email, User.id != user_id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            auth_identity = db.query(AuthIdentity).filter(
                and_(
                    AuthIdentity.user_id == user_id,
                    AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD
                )
            ).first()
            if auth_identity:
                auth_identity.identifier = new_email
        user.email = new_email

    if request.phone is not None:
        new_phone = (request.phone.strip() or None) if request.phone else None
        if new_phone and new_phone != (user.phone or ""):
            existing = db.query(User).filter(User.phone == new_phone, User.id != user_id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this phone already exists"
                )
        user.phone = new_phone

    if request.preferred_language is not None:
        pl = (request.preferred_language.strip() or None) if request.preferred_language else None
        if pl and pl not in ("ru", "uz"):
            pl = None
        user.preferred_language = pl

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "email" in err_msg.lower() or "unique" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone already used by another account"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data conflict. Check that email and phone are unique."
        )

    return UserResponse.model_validate(user)
