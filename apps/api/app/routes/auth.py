from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from uuid import UUID
import logging
from app.db import get_db

logger = logging.getLogger(__name__)
from app.deps import require_user
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
    try:
        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
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
            is_active=True
        )
        db.add(user)
        db.flush()  # Get user.id

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

        db.commit()
        db.refresh(user)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
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
    """
    # Find auth identity
    auth_identity = db.query(AuthIdentity).filter(
        and_(
            AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD,
            AuthIdentity.identifier == request.email
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
    
    db.commit()
    db.refresh(user)
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
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
    In dev mode, if user does not exist, creates a minimal user so profile can be edited.
    """
    from app.settings import get_settings
    settings = get_settings()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        if settings.APP_ENV.lower() in ("dev", "development") and str(user_id) == settings.DEFAULT_DEV_USER_ID:
            user = User(id=user_id, email="dev@example.com", full_name="Dev User", is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile (full_name, email, phone).
    If email is changed, auth identity identifier is updated so login continues to work.
    In dev mode, if user does not exist, creates them so profile save works.
    """
    from app.settings import get_settings
    settings = get_settings()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        if settings.APP_ENV.lower() in ("dev", "development"):
            user = User(
                id=user_id,
                email=request.email or "dev@example.com",
                full_name=request.full_name or "Dev User",
                phone=request.phone,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
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
