"""
Integration: tenants A and B — JWT for each, dim_shop for B only, GET /api/shops must not leak B to A.
Requires PostgreSQL (DATABASE_URL), users/auth tables, and the conftest fixture
ensure_dim_shop_and_fact_sales_for_tests (dim_shop + fact_sales DDL).
"""
import asyncio
import uuid

import httpx
import pytest
from sqlalchemy import text

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


pytestmark = pytest.mark.skipif(
    not _db_ok(),
    reason="DATABASE_URL not available or DB unreachable",
)


def _async_request(method: str, path: str, **kwargs):
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            fn = getattr(client, method.lower())
            return await fn(path, **kwargs)

    return asyncio.run(_run())


def test_get_shops_tenant_isolation_dim_shop(ensure_dim_shop_and_fact_sales_for_tests):
    schema = get_settings().DB_SCHEMA
    uid_a = uuid.uuid4()
    uid_b = uuid.uuid4()
    email_a = f"tenant_a_{uuid.uuid4().hex[:10]}@example.com"
    email_b = f"tenant_b_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestTenantIso123!"
    pw_hash = hash_password(password)
    shop_name_b = f"SHOP_B_ONLY_{uuid.uuid4().hex[:8]}"

    try:
        with SessionLocal() as db:
            db.execute(text(f"SET search_path TO {schema}, public"))
            db.add(
                User(
                    id=uid_a,
                    email=email_a,
                    is_active=True,
                )
            )
            db.add(
                User(
                    id=uid_b,
                    email=email_b,
                    is_active=True,
                )
            )
            db.flush()
            db.add(
                AuthIdentity(
                    user_id=uid_a,
                    provider=AuthProvider.EMAIL_PASSWORD,
                    identifier=email_a,
                    password_hash=pw_hash,
                )
            )
            db.add(
                AuthIdentity(
                    user_id=uid_b,
                    provider=AuthProvider.EMAIL_PASSWORD,
                    identifier=email_b,
                    password_hash=pw_hash,
                )
            )
            db.commit()

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.dim_shop (user_id, shop_name)
                    VALUES (CAST(:uid AS uuid), :name)
                    RETURNING shop_id::text
                    """
                ),
                {"uid": str(uid_b), "name": shop_name_b},
            ).fetchone()
            shop_b_id = row[0]

        ra = _async_request(
            "post",
            "/api/auth/login",
            json={"email": email_a, "password": password},
        )
        assert ra.status_code == 200, ra.text
        token_a = ra.json()["access_token"]

        rb = _async_request(
            "post",
            "/api/auth/login",
            json={"email": email_b, "password": password},
        )
        assert rb.status_code == 200, rb.text
        token_b = rb.json()["access_token"]

        r_a = _async_request(
            "get",
            "/api/shops",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r_a.status_code == 200, r_a.text
        shops_a = r_a.json().get("shops") or []
        ids_a = {s["shop_id"] for s in shops_a}
        names_a = {s.get("shop_name") for s in shops_a}
        assert str(shop_b_id) not in ids_a
        assert shop_name_b not in names_a

        r_b = _async_request(
            "get",
            "/api/shops",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r_b.status_code == 200, r_b.text
        shops_b = r_b.json().get("shops") or []
        ids_b = {s["shop_id"] for s in shops_b}
        assert str(shop_b_id) in ids_b
        assert any((s.get("shop_name") or "") == shop_name_b for s in shops_b)

    finally:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"DELETE FROM {schema}.dim_shop WHERE user_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ),
                {"a": str(uid_a), "b": str(uid_b)},
            )
            conn.execute(
                text(
                    f"DELETE FROM {schema}.refresh_tokens WHERE user_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ),
                {"a": str(uid_a), "b": str(uid_b)},
            )
            conn.execute(
                text(
                    f"DELETE FROM {schema}.auth_identities WHERE user_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ),
                {"a": str(uid_a), "b": str(uid_b)},
            )
            conn.execute(
                text(f"DELETE FROM {schema}.users WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"),
                {"a": str(uid_a), "b": str(uid_b)},
            )
