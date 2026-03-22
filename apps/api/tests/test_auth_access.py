"""
Security and access control: JWT vs X-User-Id in prod, trial guard on imports.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app import deps
from app.db import get_db
from app.main import app


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


def test_import_blocked_when_trial_expired():
    """Import returns 403 when trial_ends_at is in the past (non-admin)."""
    uid = "550e8400-e29b-41d4-a716-446655440000"
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)

    def mock_get_db():
        mock_sess = MagicMock()

        def exec_side_effect(statement, params=None):
            s = str(statement).lower()
            m = MagicMock()
            if "trial_ends_at" in s:
                m.fetchone.return_value = (past,)
            elif "email" in s and "users" in s:
                m.fetchone.return_value = ("user@example.com",)
            else:
                m.fetchone.return_value = None
            return m

        mock_sess.execute.side_effect = exec_side_effect
        yield mock_sess

    app.dependency_overrides[get_db] = mock_get_db
    try:
        with patch("app.routes.imports.ensure_dev_user_exists", lambda *a, **k: None):
            async def _call():
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://testserver",
                ) as client:
                    return await client.post(
                        "/api/import-xlsx",
                        headers={"X-User-Id": uid},
                        data={"reportType": "sales"},
                        files={
                            "file": (
                                "sales.xlsx",
                                io_bytes_xlsx_placeholder(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        },
                    )

            response = asyncio.run(_call())
        assert response.status_code == 403
        assert "Trial expired" in (response.json().get("detail") or "")
    finally:
        app.dependency_overrides.pop(get_db, None)


def io_bytes_xlsx_placeholder() -> bytes:
    """Minimal bytes; parsing runs only after access checks in this test path."""
    return b"PK\x03\x04placeholder"
