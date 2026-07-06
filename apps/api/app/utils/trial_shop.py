"""Trial plan: sync all shops, user picks one display shop via allowed_shops."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import qname
from app.deps import is_user_admin
from app.utils.tenant_shop_allowlist import get_user_allowed_shops_list, norm_shop_label, set_user_allowed_shops_list

logger = logging.getLogger(__name__)


def _user_plan(db: Session, user_id: UUID) -> str:
    row = db.execute(
        text(f"SELECT COALESCE(plan, 'trial') FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"),
        {"uid": str(user_id)},
    ).fetchone()
    return (row[0] or "trial").strip().lower() if row else "trial"


def is_trial_plan_user(db: Session, user_id: UUID) -> bool:
    if is_user_admin(user_id, db):
        return False
    plan = _user_plan(db, user_id)
    return plan in ("trial", "") or not plan


def get_effective_trial_display_shop(db: Session, user_id: UUID) -> Optional[str]:
    """Магазин к показу на trial — первый элемент allowed_shops."""
    if not is_trial_plan_user(db, user_id):
        return None
    override = get_user_allowed_shops_list(db, user_id)
    if override:
        first = str(override[0]).strip()
        if first:
            return first
    return None


def _canonicalize_loaded_shop_label(db: Session, user_id: UUID, shop_label: str) -> str:
    label = str(shop_label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="Укажите магазин")
    loaded = fetch_loaded_shop_labels(db, user_id)
    label_by_norm = {norm_shop_label(s): s for s in loaded}
    canon = label_by_norm.get(norm_shop_label(label))
    if not canon:
        raise HTTPException(
            status_code=400,
            detail="Магазин не найден среди загруженных данных",
        )
    return canon


def set_trial_permitted_shop(
    db: Session,
    user_id: UUID,
    shop_label: str,
    *,
    allow_overwrite: bool = False,
) -> str:
    """Trial: один разрешённый магазин к показу → allowed_shops."""
    if not is_trial_plan_user(db, user_id):
        raise HTTPException(status_code=400, detail="Только для trial-тарифа")
    canon = _canonicalize_loaded_shop_label(db, user_id, shop_label)
    if not allow_overwrite and get_effective_trial_display_shop(db, user_id):
        raise HTTPException(
            status_code=409,
            detail="Магазин для trial уже выбран. Обратитесь в поддержку для смены.",
        )
    set_user_allowed_shops_list(db, user_id, [canon])
    return canon


def fetch_loaded_shop_labels(db: Session, user_id: UUID) -> list[str]:
    """Distinct shop names from fact_storage_snapshot (seller-storage source of truth)."""
    rows = db.execute(
        text(
            f"""
            WITH src AS (
                SELECT NULLIF(trim(fss.shop_raw), '') AS shop_raw
                FROM {qname("fact_storage_snapshot")} fss
                WHERE fss.user_id = CAST(:uid AS uuid)
                  AND NULLIF(trim(fss.shop_raw), '') IS NOT NULL
                  AND lower(trim(fss.shop_raw)) NOT IN (
                      'не определено', 'неопределено', 'undefined', 'null',
                      '(не определено)', 'не определен'
                  )
            ),
            norm AS (
                SELECT
                    shop_raw,
                    upper(regexp_replace(trim(shop_raw), '\\s+', ' ', 'g')) AS shop_norm
                FROM src
            )
            SELECT shop_norm, MIN(shop_raw) AS label
            FROM norm
            GROUP BY shop_norm
            ORDER BY label
            """
        ),
        {"uid": str(user_id)},
    ).fetchall()
    return [str(r[1] or r[0]) for r in rows if r[0]]


def user_needs_trial_shop_selection(db: Session, user_id: UUID) -> bool:
    if not is_trial_plan_user(db, user_id):
        return False
    if get_effective_trial_display_shop(db, user_id):
        return False
    return len(fetch_loaded_shop_labels(db, user_id)) > 0


def assert_trial_shop_filter_allowed(
    db: Session,
    user_id: UUID,
    shop: Optional[str],
    shop_id: Optional[str] = None,
) -> None:
    """Trial users may only filter by all shops (no param) or their display shop."""
    if not is_trial_plan_user(db, user_id):
        return
    if shop_id:
        raise HTTPException(
            status_code=403,
            detail="Фильтр по магазину недоступен на trial-тарифе",
        )
    if not shop:
        return
    display = get_effective_trial_display_shop(db, user_id)
    if not display:
        return
    if norm_shop_label(shop) != norm_shop_label(display):
        raise HTTPException(
            status_code=403,
            detail="Этот магазин недоступен на trial. Выберите платный тариф для доступа ко всем магазинам.",
        )


def shop_is_selectable_for_trial(
    db: Session,
    user_id: UUID,
    shop_norm: str,
    *,
    trial_display: Optional[str],
) -> bool:
    if not is_trial_plan_user(db, user_id):
        return True
    if not trial_display:
        return True
    return norm_shop_label(trial_display) == norm_shop_label(shop_norm)
