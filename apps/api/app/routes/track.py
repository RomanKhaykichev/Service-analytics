"""
Публичные эндпоинты трекинга для воронки админки (без авторизации).
- POST /api/track/landing-visit — визит на лендинг
- POST /api/track/promo-try — клик «Попробовать бесплатно» в промо-окне
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.db import get_db, qname
from app.settings import get_settings

router = APIRouter()
settings = get_settings()


class TrackBody(BaseModel):
    visitor_key: str = ""


def _ensure_tracking_tables(db: Session) -> None:
    """
    Make funnel tracking resilient on fresh/prod DBs where migration was missed.
    """
    schema = settings.DB_SCHEMA
    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.landing_visits (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            visitor_key varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_landing_visits_visitor_key
        ON {schema}.landing_visits (visitor_key)
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_landing_visits_created_at
        ON {schema}.landing_visits (created_at)
    """))

    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.promo_try_clicks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            visitor_key varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_promo_try_clicks_visitor_key
        ON {schema}.promo_try_clicks (visitor_key)
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_promo_try_clicks_created_at
        ON {schema}.promo_try_clicks (created_at)
    """))


@router.post("/track/landing-visit")
async def track_landing_visit(body: TrackBody, db: Session = Depends(get_db)):
    """Учёт визита на лендинг (уникальность по visitor_key не принудительная — считаем distinct в админке)."""
    key = (body.visitor_key or "").strip()[:64] or None
    if not key:
        return {"ok": False, "error": "visitor_key required"}
    try:
        _ensure_tracking_tables(db)
        db.execute(
            text(f"INSERT INTO {qname('landing_visits')} (visitor_key, created_at) VALUES (:k, now())"),
            {"k": key},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@router.post("/track/promo-try")
async def track_promo_try(body: TrackBody, db: Session = Depends(get_db)):
    """Учёт клика «Попробовать бесплатно» в промо-окне."""
    key = (body.visitor_key or "").strip()[:64] or None
    if not key:
        return {"ok": False, "error": "visitor_key required"}
    try:
        _ensure_tracking_tables(db)
        db.execute(
            text(f"INSERT INTO {qname('promo_try_clicks')} (visitor_key, created_at) VALUES (:k, now())"),
            {"k": key},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    return {"ok": True}
