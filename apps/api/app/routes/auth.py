from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from uuid import UUID
from app.db import get_db
from app.deps import require_user
from app.models import User, AuthIdentity, RefreshToken
from app.models.auth_identity import AuthProvider
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
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
        is_active=True
    )
    db.add(user)
    db.flush()  # Get user.id
    
    # Create auth identity
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
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user.
    Requires Bearer access token or X-User-Id header (dev mode).
    """
    user_id = require_user(request)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)
