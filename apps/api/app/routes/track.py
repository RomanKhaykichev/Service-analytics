"""
Эндпоинты трекинга для воронки и метрик админки.
- POST /api/track/landing-visit — визит на лендинг (без авторизации)
- POST /api/track/promo-try — клик «Попробовать бесплатно» (без авторизации)
- POST /api/track/training-page — открытие страницы «Обучение» (авторизация)
- POST /api/track/tariff-payment-open — открытие окна «Оплата тарифа» (авторизация)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from uuid import UUID

from app.db import get_db, qname
from app.deps import require_user
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

    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.training_page_views (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_training_page_views_created_at
        ON {schema}.training_page_views (created_at)
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_training_page_views_user_id
        ON {schema}.training_page_views (user_id)
    """))

    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.tariff_payment_opens (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_tariff_payment_opens_created_at
        ON {schema}.tariff_payment_opens (created_at)
    """))
    db.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_tariff_payment_opens_user_id
        ON {schema}.tariff_payment_opens (user_id)
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


@router.post("/track/training-page")
async def track_training_page(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Учёт открытия страницы «Обучение»."""
    try:
        _ensure_tracking_tables(db)
        db.execute(
            text(f"INSERT INTO {qname('training_page_views')} (user_id, created_at) VALUES (:uid, now())"),
            {"uid": user_id},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@router.post("/track/tariff-payment-open")
async def track_tariff_payment_open(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Учёт открытия окна «Оплата тарифа»."""
    try:
        _ensure_tracking_tables(db)
        db.execute(
            text(f"INSERT INTO {qname('tariff_payment_opens')} (user_id, created_at) VALUES (:uid, now())"),
            {"uid": user_id},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    return {"ok": True}
