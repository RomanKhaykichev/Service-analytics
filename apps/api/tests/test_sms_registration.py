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

from app.db import SessionLocal, engine, get_db
from app.deps import require_user
from app.main import app
from app.pending_registration import cleanup_expired_pending
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
    return f"90{uuid.uuid4().int % 10_000_000:07d}"  # 9 digits after +998


def _async_post(path: str, json: dict, headers: dict | None = None):
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=json, headers=headers or {})

    return asyncio.run(_run())


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_register_creates_pending_only_no_user_created(unique_email, phone_digits):
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
    assert "pending_id" in data
    assert "phone_masked" in data
    assert "access_token" not in data
    assert "refresh_token" not in data
    pending_id = data["pending_id"]
    with engine.connect() as c:
        users_cnt = c.execute(text("SELECT count(*) FROM app.users WHERE lower(email)=lower(:email)"), {"email": unique_email}).scalar()
        ids_cnt = c.execute(text("SELECT count(*) FROM app.auth_identities WHERE lower(identifier)=lower(:email)"), {"email": unique_email}).scalar()
        pending_cnt = c.execute(text("SELECT count(*) FROM app.pending_registrations WHERE id=CAST(:pid AS uuid)"), {"pid": pending_id}).scalar()
    assert int(users_cnt or 0) == 0
    assert int(ids_cnt or 0) == 0
    assert int(pending_cnt or 0) == 1


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_verify_creates_user_and_identity_and_deletes_pending(unique_email, phone_digits):
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
    pending_id = reg.json()["pending_id"]

    r = _async_post(
        "/api/auth/verify-phone",
        {
            "pending_id": pending_id,
            "code": "123456",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("access_token")
    assert data.get("refresh_token")
    assert data.get("user", {}).get("phone_verified_at")
    with engine.connect() as c:
        users_cnt = c.execute(text("SELECT count(*) FROM app.users WHERE lower(email)=lower(:email)"), {"email": unique_email}).scalar()
        ids_cnt = c.execute(text("SELECT count(*) FROM app.auth_identities WHERE lower(identifier)=lower(:email)"), {"email": unique_email}).scalar()
        pending_cnt = c.execute(text("SELECT count(*) FROM app.pending_registrations WHERE id=CAST(:pid AS uuid)"), {"pid": pending_id}).scalar()
    assert int(users_cnt or 0) == 1
    assert int(ids_cnt or 0) == 1
    assert int(pending_cnt or 0) == 0


def test_import_forbidden_when_phone_not_verified():
    uid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

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
    app.dependency_overrides[require_user] = lambda: uid
    try:
        with patch("app.routes.imports.ensure_dev_user_exists", lambda *a, **k: None):
            transport = httpx.ASGITransport(app=app)
            async def _run():
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    return await client.post(
                        "/api/import-xlsx",
                        headers={},
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
        app.dependency_overrides.pop(require_user, None)
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
        pending_id = reg.json()["pending_id"]

        # register = 1 SMS; max 3 per 15 min → 2 resends OK, 3rd resend → 429
        r1 = _async_post("/api/auth/resend-phone-otp", {"pending_id": pending_id})
        r2 = _async_post("/api/auth/resend-phone-otp", {"pending_id": pending_id})
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        r3 = _async_post("/api/auth/resend-phone-otp", {"pending_id": pending_id})
        assert r3.status_code == 429, r3.text


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_repeat_register_updates_pending_and_resends_otp_without_unique_email_error(unique_email, phone_digits):
    first_phone = f"+998{phone_digits}"
    second_phone = f"+99891{uuid.uuid4().int % 10_000_000:07d}"
    with patch("app.routes.auth.generate_otp_code", return_value="222222"):
        r1 = _async_post(
            "/api/auth/register",
            {
                "email": unique_email,
                "password": "secret12",
                "full_name": "First Name",
                "phone": first_phone,
                "consent_processing": True,
            },
        )
    assert r1.status_code == 201, r1.text
    pending_id_1 = r1.json()["pending_id"]

    with patch("app.routes.auth.generate_otp_code", return_value="333333"):
        r2 = _async_post(
            "/api/auth/register",
            {
                "email": unique_email,
                "password": "secret34",
                "full_name": "Second Name",
                "phone": second_phone,
                "consent_processing": True,
            },
        )
    assert r2.status_code == 201, r2.text
    pending_id_2 = r2.json()["pending_id"]
    assert pending_id_1 == pending_id_2

    with engine.connect() as c:
        row = c.execute(
            text(
                """
                SELECT full_name, phone
                FROM app.pending_registrations
                WHERE id = CAST(:pid AS uuid)
                """
            ),
            {"pid": pending_id_1},
        ).fetchone()
    assert row is not None
    assert row[0] == "Second Name"
    assert row[1] == second_phone


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_expired_pending_cannot_verify(unique_email, phone_digits):
    with patch("app.routes.auth.generate_otp_code", return_value="444444"):
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
    pending_id = reg.json()["pending_id"]
    with engine.begin() as c:
        c.execute(
            text("UPDATE app.pending_registrations SET expires_at = now() - interval '1 minute' WHERE id = CAST(:pid AS uuid)"),
            {"pid": pending_id},
        )
    r = _async_post("/api/auth/verify-phone", {"pending_id": pending_id, "code": "444444"})
    # cleanup_expired_pending runs before lookup; expired row is deleted → 404
    assert r.status_code == 404, r.text
    assert "not found" in (r.json().get("detail") or "").lower()


def test_cleanup_expired_pending_deletes_rows(unique_email, phone_digits):
    stale_id = str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(
            text(
                """INSERT INTO app.pending_registrations
                (id, email, phone, password_hash, consent_processing, expires_at, attempts)
                VALUES (CAST(:id AS uuid), :email, :phone, 'hash', true, now() - interval '1 hour', 0)"""
            ),
            {"id": stale_id, "email": unique_email, "phone": f"+998{phone_digits}"},
        )
    with SessionLocal() as db:
        db.execute(text("SET search_path TO app, public"))
        deleted = cleanup_expired_pending(db)
        db.commit()
        assert deleted >= 1
    with engine.connect() as c:
        n = c.execute(
            text("SELECT count(*) FROM app.pending_registrations WHERE id=CAST(:id AS uuid)"),
            {"id": stale_id},
        ).scalar()
    assert int(n or 0) == 0


@patch("app.phone_verification.send_registration_otp_sms", lambda *a, **k: None)
def test_register_cleanup_removes_expired_pending_other_email(unique_email, phone_digits):
    stale_email = f"stale_{uuid.uuid4().hex[:12]}@example.com"
    stale_phone = f"+99890{uuid.uuid4().int % 10_000_000:07d}"
    stale_id = str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(
            text(
                """INSERT INTO app.pending_registrations
                (id, email, phone, password_hash, consent_processing, expires_at, attempts)
                VALUES (CAST(:id AS uuid), :email, :phone, 'hash', true, now() - interval '1 day', 0)"""
            ),
            {"id": stale_id, "email": stale_email, "phone": stale_phone},
        )
    body = {
        "email": unique_email,
        "password": "secret12",
        "full_name": "Test User",
        "phone": f"+998{phone_digits}",
        "consent_processing": True,
    }
    r = _async_post("/api/auth/register", body)
    assert r.status_code == 201, r.text
    with engine.connect() as c:
        n = c.execute(
            text("SELECT count(*) FROM app.pending_registrations WHERE id=CAST(:id AS uuid)"),
            {"id": stale_id},
        ).scalar()
    assert int(n or 0) == 0
