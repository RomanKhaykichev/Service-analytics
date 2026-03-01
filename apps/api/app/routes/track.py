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


@router.post("/track/landing-visit")
async def track_landing_visit(body: TrackBody, db: Session = Depends(get_db)):
    """Учёт визита на лендинг (уникальность по visitor_key не принудительная — считаем distinct в админке)."""
    key = (body.visitor_key or "").strip()[:64] or None
    if not key:
        return {"ok": False, "error": "visitor_key required"}
    try:
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
        db.execute(
            text(f"INSERT INTO {qname('promo_try_clicks')} (visitor_key, created_at) VALUES (:k, now())"),
            {"k": key},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    return {"ok": True}
