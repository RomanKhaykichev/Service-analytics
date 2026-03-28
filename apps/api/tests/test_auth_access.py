"""
Security and access control: JWT vs X-User-Id in prod, trial guard on imports.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app import deps
from app.auth import hash_password
from app.db import SessionLocal, engine
from app.main import app
from app.models import User, AuthIdentity
from app.models.auth_identity import AuthProvider
from app.settings import get_settings


def _db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.parametrize(
    "app_env,env",
    [
        ("prod", ""),
        ("dev", "prod"),
    ],
)
def test_auth_requires_jwt_in_prod_x_user_id_rejected(app_env, env):
    """In production (APP_ENV or ENV), X-User-Id alone must not authenticate (401)."""
    orig_app_env = deps.settings.APP_ENV
    orig_env = getattr(deps.settings, "ENV", "")
    try:
        deps.settings.APP_ENV = app_env
        deps.settings.ENV = env
        request = MagicMock()
        request.headers.get = lambda k, d=None: (
            "550e8400-e29b-41d4-a716-446655440000" if k == "X-User-Id" else d
        )
        with pytest.raises(HTTPException) as ei:
            deps.require_user(request, None)
        assert ei.value.status_code == 401
    finally:
        deps.settings.APP_ENV = orig_app_env
        deps.settings.ENV = orig_env


@pytest.mark.skipif(not _db_ok(), reason="DATABASE_URL not available or DB unreachable")
def test_import_blocked_when_trial_expired():
    """Import returns 403 when trial_ends_at is in the past (non-admin); real JWT via /api/auth/login."""
    schema = get_settings().DB_SCHEMA
    uid = uuid.uuid4()
    email = f"trial_expired_{uuid.uuid4().hex[:12]}@example.com"
    password = "TrialExpiredTest123!"
    pw_hash = hash_password(password)
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)

    try:
        with SessionLocal() as db:
            db.execute(text(f"SET search_path TO {schema}, public"))
            db.add(User(id=uid, email=email, is_active=True))
            db.add(
                AuthIdentity(
                    user_id=uid,
                    provider=AuthProvider.EMAIL_PASSWORD,
                    identifier=email,
                    password_hash=pw_hash,
                )
            )
            db.commit()

        with engine.begin() as conn:
            conn.execute(
                text(
                    f"UPDATE {schema}.users SET trial_ends_at = :t, plan = COALESCE(plan, 'trial') "
                    f"WHERE id = CAST(:uid AS uuid)"
                ),
                {"t": past, "uid": str(uid)},
            )

        async def _login_and_import():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                lr = await client.post(
                    "/api/auth/login",
                    json={"email": email, "password": password},
                )
                assert lr.status_code == 200, lr.text
                token = lr.json()["access_token"]
                return await client.post(
                    "/api/import-xlsx",
                    headers={"Authorization": f"Bearer {token}"},
                    data={"reportType": "sales"},
                    files={
                        "file": (
                            "sales.xlsx",
                            io_bytes_xlsx_placeholder(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    },
                )

        response = asyncio.run(_login_and_import())
        assert response.status_code == 403
        assert "Trial expired" in (response.json().get("detail") or "")
    finally:
        with engine.begin() as conn:
            try:
                conn.execute(
                    text(
                        f"DELETE FROM {schema}.refresh_tokens WHERE user_id = CAST(:uid AS uuid)"
                    ),
                    {"uid": str(uid)},
                )
            except Exception:
                pass
            conn.execute(
                text(
                    f"DELETE FROM {schema}.auth_identities WHERE user_id = CAST(:uid AS uuid)"
                ),
                {"uid": str(uid)},
            )
            conn.execute(
                text(f"DELETE FROM {schema}.users WHERE id = CAST(:uid AS uuid)"),
                {"uid": str(uid)},
            )


def io_bytes_xlsx_placeholder() -> bytes:
    """Minimal bytes; parsing runs only after access checks in this test path."""
    return b"PK\x03\x04placeholder"
