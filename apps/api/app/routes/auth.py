from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta, date
from uuid import UUID
import logging
import hmac
from app.db import get_db, qname
from app.settings import get_settings
from sqlalchemy import text

logger = logging.getLogger(__name__)
from app.deps import require_user, is_user_admin
from app.models import User, AuthIdentity, RefreshToken, VerificationCode, PendingRegistration
from app.models.verification_code import VerificationChannel
from app.models.auth_identity import AuthProvider
from app.schemas.auth import (
    RegisterRequest,
    RegisterVerifyPendingResponse,
    VerifyPhoneRequest,
    ResendPhoneOtpRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    UpdateProfileRequest,
    AuthResponse,
    TokenResponse,
    UserResponse,
)
from app.pending_registration import cleanup_expired_pending
from app.phone_verification import (
    assert_send_rate_limit,
    assert_verify_fail_rate_limit,
    create_sms_verification,
    generate_otp_code,
    mask_phone,
    normalize_uz_phone,
    otp_hash,
    pending_expires_at,
    record_verify_fail,
    send_registration_otp_sms,
)
from app.utils.login_events import record_login_event, touch_last_login_at
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


def _refresh_token_expires_at() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TTL_DAYS)


def _persist_refresh_token(db: Session, user_id: UUID, refresh_token: str) -> str:
    """
    Save refresh token hash. On rare duplicate hash, revoke the conflict and retry once with a new token.
    Returns the refresh token that was persisted (may differ from input after retry).
    """
    token = refresh_token
    expires_at = _refresh_token_expires_at()
    for attempt in range(2):
        token_hash = hash_token(token)
        conflict = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if conflict and conflict.revoked_at is None:
            conflict.revoked_at = datetime.now(timezone.utc)
        db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        try:
            db.flush()
            return token
        except IntegrityError:
            db.rollback()
            if attempt == 0:
                token = create_refresh_token(str(user_id))
                continue
            raise
    return token


def _is_prod_cookie_mode(settings) -> bool:
    """Same idea as deps._is_production_env: secure / SameSite=None for real deployments."""
    if (getattr(settings, "ENV", "") or "").strip().lower() == "prod":
        return True
    return (settings.APP_ENV or "").lower() == "prod"


def _set_refresh_token_cookie(response: Response, refresh_token: str, settings) -> None:
    """HttpOnly refresh cookie; optional COOKIE_DOMAIN in prod (e.g. .profiboard.uz for Pages + API)."""
    is_prod = _is_prod_cookie_mode(settings)
    max_age = settings.REFRESH_TTL_DAYS * 24 * 60 * 60
    kwargs = {
        "key": "refresh_token",
        "value": refresh_token,
        "httponly": True,
        "secure": is_prod,
        "samesite": "none" if is_prod else "lax",
        "max_age": max_age,
        "path": "/api/auth",
    }
    domain = (getattr(settings, "COOKIE_DOMAIN", None) or "").strip()
    if is_prod and domain:
        kwargs["domain"] = domain
    response.set_cookie(**kwargs)  # type: ignore[arg-type]


def _delete_refresh_token_cookie(response: Response, settings) -> None:
    kwargs = {"key": "refresh_token", "path": "/api/auth"}
    domain = (getattr(settings, "COOKIE_DOMAIN", None) or "").strip()
    if _is_prod_cookie_mode(settings) and domain:
        kwargs["domain"] = domain
    response.delete_cookie(**kwargs)


def _enrich_user_trial_info(resp: UserResponse, user_id: UUID, db: Session) -> None:
  """
  Fill plan / trial_ends_at / trial_days_left for current user
  based on users.plan and users.trial_ends_at (raw SQL, т.к. колонок нет в ORM-модели).
  """
  try:
      row = db.execute(
          text(
              f"SELECT COALESCE(plan,'trial') AS plan, trial_ends_at "
              f"FROM {qname('users')} WHERE id = :uid"
          ),
          {"uid": user_id},
      ).fetchone()
  except Exception:
      return

  if not row:
      return

  plan_val = (row[0] or "trial")
  trial_ends_at = row[1]

  # Админы: без ограничения по сроку доступа; на фронте тариф показывается как «Admin» по is_admin.
  if is_user_admin(user_id, db):
      resp.plan = plan_val
      resp.trial_ends_at = None
      resp.trial_days_left = None
      return

  trial_days_left = None
  if trial_ends_at:
      try:
          if isinstance(trial_ends_at, str):
              te = date.fromisoformat(trial_ends_at[:10])
          else:
              te = getattr(trial_ends_at, "date", lambda: trial_ends_at)() if hasattr(trial_ends_at, "date") else trial_ends_at
          trial_days_left = (te - date.today()).days
      except Exception:
          trial_days_left = None

  resp.plan = plan_val
  if trial_ends_at:
      try:
          resp.trial_ends_at = trial_ends_at.isoformat() if hasattr(trial_ends_at, "isoformat") else str(trial_ends_at)
      except Exception:
          resp.trial_ends_at = str(trial_ends_at)
  else:
      resp.trial_ends_at = None
  resp.trial_days_left = trial_days_left


@router.post("/register", response_model=RegisterVerifyPendingResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Start registration by creating/updating pending draft and sending SMS OTP.
    User/auth_identity are created only after /verify-phone succeeds.
    """
    if not request.consent_processing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent to personal data processing is required"
        )
    settings = get_settings()
    try:
        cleanup_expired_pending(db)
        try:
            phone_norm = normalize_uz_phone(request.phone)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valid phone number is required",
            )

        assert_send_rate_limit(db, phone_norm)

        email_norm = str(request.email).strip().lower()
        existing_user = db.query(User).filter(func.lower(User.email) == email_norm).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        existing_phone = db.query(User).filter(User.phone == phone_norm).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists"
            )

        existing_identity = db.query(AuthIdentity).filter(
            and_(
                AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD,
                func.lower(AuthIdentity.identifier) == email_norm
            )
        ).first()
        if existing_identity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        password_hash = hash_password(request.password)
        pending = db.query(PendingRegistration).filter(func.lower(PendingRegistration.email) == email_norm).first()
        if pending:
            # Reuse existing pending record (even if expired) and refresh the data.
            pending.full_name = request.full_name or None
            pending.phone = phone_norm
            pending.password_hash = password_hash
            pending.consent_processing = request.consent_processing
            pending.expires_at = pending_expires_at(hours=settings.PENDING_TTL_HOURS)
        else:
            pending = PendingRegistration(
                email=email_norm,
                full_name=request.full_name or None,
                phone=phone_norm,
                password_hash=password_hash,
                consent_processing=request.consent_processing,
                expires_at=pending_expires_at(hours=settings.PENDING_TTL_HOURS),
                attempts=0,
            )
            db.add(pending)
        db.flush()

        code_plain = generate_otp_code()
        create_sms_verification(db, phone_norm, code_plain, pending_id=pending.id)

        try:
            send_registration_otp_sms(phone_norm, code_plain)
        except Exception as e:
            logger.exception("SMS send failed during registration")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to send verification SMS: {str(e)}",
            )

        db.commit()
        return RegisterVerifyPendingResponse(
            pending_id=pending.id,
            phone_masked=mask_phone(phone_norm),
            expires_in_sec=300,
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


def _issue_auth_response(user: User, db: Session, response: Response) -> AuthResponse:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    refresh_token_hash = hash_token(refresh_token)
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TTL_DAYS)
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    now_utc = datetime.now(timezone.utc)
    touch_last_login_at(db, user.id, now_utc)
    record_login_event(db, user.id, now_utc)
    db.commit()
    db.refresh(user)
    user_resp = UserResponse.model_validate(user)
    user_resp.is_admin = is_user_admin(user.id, db)
    _enrich_user_trial_info(user_resp, user.id, db)
    try:
        _set_refresh_token_cookie(response, refresh_token, settings)
    except Exception as e:
        logger.warning("Failed to set refresh_token cookie: %s", e)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp,
    )


@router.post("/verify-phone", response_model=AuthResponse)
async def verify_phone(
    request: VerifyPhoneRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Confirm SMS code and only then create user/auth identity and issue tokens."""

    code_in = (request.code or "").strip().replace(" ", "")
    if len(code_in) != 6 or not code_in.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter the 6-digit verification code",
        )

    cleanup_expired_pending(db)

    pending = db.query(PendingRegistration).filter(PendingRegistration.id == request.pending_id).first()
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending registration not found")

    now_utc = datetime.now(timezone.utc)
    if pending.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pending registration expired. Start again.")

    try:
        phone_norm = normalize_uz_phone(request.phone) if request.phone else normalize_uz_phone(pending.phone)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
    if phone_norm != normalize_uz_phone(pending.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone does not match pending registration")

    assert_verify_fail_rate_limit(db, phone_norm)

    vc = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.pending_id == pending.id,
            VerificationCode.destination == phone_norm,
            or_(
                VerificationCode.channel == VerificationChannel.SMS,
                VerificationCode.channel == "sms",
            ),
            VerificationCode.consumed_at.is_(None),
            VerificationCode.expires_at > now_utc,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not vc:
        record_verify_fail(db, None, phone_norm)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired or missing. Request a new code.",
        )

    expected_hash = otp_hash(code_in)
    if not hmac.compare_digest(vc.code_hash, expected_hash):
        record_verify_fail(db, None, phone_norm)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    vc.consumed_at = now_utc
    if db.query(User).filter(func.lower(User.email) == str(pending.email).lower()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")
    if db.query(User).filter(User.phone == phone_norm).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this phone number already exists")
    if db.query(AuthIdentity).filter(
        and_(
            AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD,
            func.lower(AuthIdentity.identifier) == str(pending.email).lower(),
        )
    ).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")
    user = User(
        email=pending.email,
        full_name=pending.full_name or None,
        phone=phone_norm,
        is_active=True,
        phone_verified_at=now_utc,
    )
    db.add(user)
    db.flush()
    try:
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
        logger.debug("trial_ends_at/consent update skipped: %s", e)

    auth_identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        identifier=pending.email,
        password_hash=pending.password_hash,
    )
    db.add(auth_identity)
    db.delete(pending)

    return _issue_auth_response(user, db, response)


@router.post("/resend-phone-otp")
async def resend_phone_otp(
    body: ResendPhoneOtpRequest,
    db: Session = Depends(get_db),
):
    """Resend SMS OTP for pending registration (rate-limited)."""
    pending = db.query(PendingRegistration).filter(PendingRegistration.id == body.pending_id).first()
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending registration not found")
    if pending.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pending registration expired. Start again.")
    try:
        phone_norm = normalize_uz_phone(pending.phone or "")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No phone on file")

    assert_send_rate_limit(db, phone_norm)
    code_plain = generate_otp_code()
    create_sms_verification(db, phone_norm, code_plain, pending_id=pending.id)
    try:
        send_registration_otp_sms(phone_norm, code_plain)
    except Exception as e:
        logger.exception("resend SMS failed")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to send SMS: {str(e)}",
        )
    db.commit()
    return {"ok": True, "expires_in_sec": 300}


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response,
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

    if user.phone and str(user.phone).strip() and user.phone_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone not verified",
        )

    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    refresh_token = _persist_refresh_token(db, user.id, refresh_token)
    
    now_utc = datetime.now(timezone.utc)
    touch_last_login_at(db, user.id, now_utc)
    record_login_event(db, user.id, now_utc)
    db.commit()
    db.refresh(user)
    user_resp = UserResponse.model_validate(user)
    user_resp.is_admin = is_user_admin(user.id, db)
    _enrich_user_trial_info(user_resp, user.id, db)
    # Set refresh token as HttpOnly cookie for secure storage in browser
    try:
        settings = get_settings()
        _set_refresh_token_cookie(response, refresh_token, settings)
    except Exception as e:
        logger.warning("Failed to set refresh_token cookie: %s", e)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request_data: RefreshRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Источник refresh-токена:
    1) HttpOnly cookie refresh_token (основной путь)
    2) request_data.refresh_token (fallback для старых клиентов)

    На каждом успешном refresh токен ротируется:
    старый помечается revoked, новый сохраняется и отправляется клиенту.
    """
    # Определяем сырой refresh-токен: cookie приоритетнее тела запроса
    raw_refresh_token: str | None = request.cookies.get("refresh_token") or request_data.refresh_token
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token"
        )
    try:
        # Decode refresh token
        payload = decode_token(raw_refresh_token)
        
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

        # Disabled users must not receive new tokens.
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            # Proactively revoke current refresh token if it exists in DB.
            try:
                refresh_token_hash = hash_token(raw_refresh_token)
                db_refresh_token = db.query(RefreshToken).filter(
                    and_(
                        RefreshToken.token_hash == refresh_token_hash,
                        RefreshToken.user_id == user_id,
                        RefreshToken.revoked_at.is_(None),
                    )
                ).first()
                if db_refresh_token:
                    db_refresh_token.revoked_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                db.rollback()
            _delete_refresh_token_cookie(response, get_settings())
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive"
            )
        
        # Find refresh token in database
        refresh_token_hash = hash_token(raw_refresh_token)
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
        new_refresh_token = _persist_refresh_token(db, user_id, new_refresh_token)
        
        now_utc = datetime.now(timezone.utc)
        touch_last_login_at(db, user_id, now_utc)
        record_login_event(db, user_id, now_utc)
        db.commit()

        # Обновляем HttpOnly cookie с новым refresh-токеном
        try:
            settings = get_settings()
            _set_refresh_token_cookie(response, new_refresh_token, settings)
        except Exception as e:
            logger.warning("Failed to refresh refresh_token cookie: %s", e)

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
    request_data: LogoutRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking refresh token.
    Refresh-токен берётся из cookie или тела запроса (для старых клиентов).
    В любом случае cookie с refresh_token удаляется.
    """
    raw_refresh_token: str | None = request.cookies.get("refresh_token") or request_data.refresh_token
    if not raw_refresh_token:
        # Даже если токена нет, всё равно чистим cookie и возвращаем успех
        _delete_refresh_token_cookie(response, get_settings())
        return {"message": "Logged out successfully"}

    refresh_token_hash = hash_token(raw_refresh_token)
    
    db_refresh_token = db.query(RefreshToken).filter(
        and_(
            RefreshToken.token_hash == refresh_token_hash,
            RefreshToken.revoked_at.is_(None)
        )
    ).first()
    
    if db_refresh_token:
        db_refresh_token.revoked_at = datetime.now(timezone.utc)
        db.commit()

    # Удаляем refresh_token cookie в браузере
    try:
        _delete_refresh_token_cookie(response, get_settings())
    except Exception as e:
        logger.warning("Failed to delete refresh_token cookie: %s", e)

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
    _enrich_user_trial_info(resp, user_id, db)
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

    if request.new_password is not None:
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        auth_identity = db.query(AuthIdentity).filter(
            and_(
                AuthIdentity.user_id == user_id,
                AuthIdentity.provider == AuthProvider.EMAIL_PASSWORD
            )
        ).first()
        if auth_identity:
            auth_identity.password_hash = hash_password(request.new_password)
        else:
            # Если записи входа по email/паролю ещё нет (старые/импортированные аккаунты),
            # создаём её, чтобы вход по новому паролю работал.
            email = (user.email or "").strip() if user.email else ""
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email must be set before changing password"
                )
            password_hash = hash_password(request.new_password)
            new_identity = AuthIdentity(
                user_id=user.id,
                provider=AuthProvider.EMAIL_PASSWORD,
                identifier=email,
                password_hash=password_hash,
            )
            db.add(new_identity)

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

    resp = UserResponse.model_validate(user)
    _enrich_user_trial_info(resp, user_id, db)
    return resp
