"""
SMS registration + verify-phone + phone guard on imports.
Requires PostgreSQL (DATABASE_URL) and applied migrations including 20260155.
"""
import asyncio
import os
import uuid
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import text

from app.db import engine, get_db
from app.main import app
def _db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_ok(),
    reason="DATABASE_URL not available or DB unreachable",
)


@pytest.fixture
def unique_email():
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def phone_digits():
    return "90" + uuid.uuid4().hex[:7]  # 9 digits after +998


def _async_post(path: str, json: dict, headers: dict | None = None):
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=json, headers=headers or {})

    return asyncio.run(_run())


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_register_does_not_issue_tokens_returns_next_verify_phone(unique_email, phone_digits):
    body = {
        "email": unique_email,
        "password": "secret12",
        "full_name": "Test User",
        "phone": f"+998{phone_digits}",
        "consent_processing": True,
    }
    r = _async_post("/api/auth/register", body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data.get("next") == "verify_phone"
    assert "user_id" in data
    assert "phone_masked" in data
    assert "access_token" not in data
    assert "refresh_token" not in data


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_verify_phone_sets_phone_verified_at_and_issues_tokens(unique_email, phone_digits):
    with patch("app.routes.auth.generate_otp_code", return_value="123456"):
        reg = _async_post(
            "/api/auth/register",
            {
                "email": unique_email,
                "password": "secret12",
                "full_name": "Test User",
                "phone": f"+998{phone_digits}",
                "consent_processing": True,
            },
        )
    assert reg.status_code == 201, reg.text
    uid = reg.json()["user_id"]

    r = _async_post(
        "/api/auth/verify-phone",
        {
            "user_id": uid,
            "email": unique_email,
            "phone": f"+998{phone_digits}",
            "code": "123456",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("access_token")
    assert data.get("refresh_token")
    assert data.get("user", {}).get("phone_verified_at")


def test_import_forbidden_when_phone_not_verified():
    uid = "550e8400-e29b-41d4-a716-446655440000"

    def mock_get_db():
        from unittest.mock import MagicMock

        mock_sess = MagicMock()

        def exec_side_effect(statement, params=None):
            s = str(statement).lower()
            m = MagicMock()
            if "phone_verified_at" in s and "users" in s and "where" in s:
                m.fetchone.return_value = ("+998901234567", None)
            elif "trial_ends_at" in s:
                m.fetchone.return_value = (None,)
            elif "email" in s and "users" in s:
                m.fetchone.return_value = ("u@example.com",)
            else:
                m.fetchone.return_value = None
            return m

        mock_sess.execute.side_effect = exec_side_effect
        yield mock_sess

    app.dependency_overrides[get_db] = mock_get_db
    try:
        with patch("app.routes.imports.ensure_dev_user_exists", lambda *a, **k: None):
            transport = httpx.ASGITransport(app=app)
            async def _run():
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    return await client.post(
                        "/api/import-xlsx",
                        headers={"X-User-Id": uid},
                        data={"reportType": "sales"},
                        files={
                            "file": (
                                "sales.xlsx",
                                b"PK\x03\x04",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        },
                    )
            r = asyncio.run(_run())
        assert r.status_code == 403
        assert "Phone not verified" in (r.json().get("detail") or "")
    finally:
        app.dependency_overrides.pop(get_db, None)


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_rate_limit_send_otp(unique_email, phone_digits):
    with patch("app.routes.auth.generate_otp_code", return_value="111111"):
        body = {
            "email": unique_email,
            "password": "secret12",
            "full_name": "Test User",
            "phone": f"+998{phone_digits}",
            "consent_processing": True,
        }
        reg = _async_post("/api/auth/register", body)
        assert reg.status_code == 201
        uid = reg.json()["user_id"]
        email = unique_email

        # register = 1 SMS; max 3 per 15 min → 2 resends OK, 3rd resend → 429
        r1 = _async_post("/api/auth/resend-phone-otp", {"user_id": uid, "email": email})
        r2 = _async_post("/api/auth/resend-phone-otp", {"user_id": uid, "email": email})
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        r3 = _async_post("/api/auth/resend-phone-otp", {"user_id": uid, "email": email})
        assert r3.status_code == 429, r3.text
