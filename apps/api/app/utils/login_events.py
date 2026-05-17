"""Запись входов пользователей в login_events для метрик админки."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import qname
from app.settings import get_settings

logger = logging.getLogger(__name__)

_table_ready: bool | None = None


def ensure_login_events_table(db: Session) -> bool:
    """Создать app.login_events при отсутствии (идемпотентно)."""
    global _table_ready
    if _table_ready is True:
        return True

    schema = get_settings().DB_SCHEMA
    try:
        r = db.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = 'login_events'"
            ),
            {"s": schema},
        ).fetchone()
        if r:
            _table_ready = True
            return True

        db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {qname('login_events')} (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL REFERENCES {qname('users')}(id) ON DELETE CASCADE,
                    logged_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        db.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_login_events_logged_at "
                f"ON {qname('login_events')} (logged_at)"
            )
        )
        db.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_login_events_user_id "
                f"ON {qname('login_events')} (user_id)"
            )
        )
        db.commit()
        _table_ready = True
        logger.info("login_events: таблица создана в схеме %s", schema)
        return True
    except Exception as e:
        logger.warning("ensure_login_events_table failed: %s", e)
        db.rollback()
        return False


def record_login_event(db: Session, user_id: UUID, logged_at: datetime | None = None) -> None:
    """Зафиксировать вход (логин, refresh, завершение регистрации)."""
    if not ensure_login_events_table(db):
        return
    now = logged_at or datetime.now(timezone.utc)
    try:
        db.execute(
            text(f"INSERT INTO {qname('login_events')} (user_id, logged_at) VALUES (:uid, :now)"),
            {"uid": user_id, "now": now},
        )
    except Exception as e:
        logger.warning("record_login_event failed for %s: %s", user_id, e)


def touch_last_login_at(db: Session, user_id: UUID, logged_at: datetime | None = None) -> None:
    now = logged_at or datetime.now(timezone.utc)
    try:
        db.execute(
            text(f"UPDATE {qname('users')} SET last_login_at = :now WHERE id = :uid"),
            {"now": now, "uid": user_id},
        )
    except Exception as e:
        logger.debug("last_login_at update skipped: %s", e)
