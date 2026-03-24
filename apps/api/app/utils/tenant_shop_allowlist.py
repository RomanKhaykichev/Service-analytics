"""Админский список разрешённых магазинов для пользователя (override поверх правил тарифа)."""
from __future__ import annotations

import json
import re
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import qname

UNDEFINED_SHOP_SQL_LIST = (
    "'не определено','неопределено','undefined','null','(не определено)','не определен'"
)


def norm_shop_label(s: str) -> str:
    s2 = re.sub(r"\s+", " ", str(s).strip())
    return s2.upper()


def get_user_allowed_shops_list(db: Session, user_id: UUID) -> Optional[list[str]]:
    """
    None — выбор магазинов по правилам тарифа (авто).
    Непустой список — только эти витринные названия магазинов разрешены в UI и при импорте storage/inventory.
    """
    try:
        row = db.execute(
            text(
                f"SELECT allowed_shops FROM {qname('users')} "
                "WHERE id = CAST(:uid AS uuid)"
            ),
            {"uid": str(user_id)},
        ).fetchone()
    except Exception:
        return None
    if not row or row[0] is None:
        return None
    raw = row[0]
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, list):
        return None
    out = [str(x).strip() for x in data if str(x).strip()]
    return out if out else None


def set_user_allowed_shops_list(db: Session, user_id: UUID, shops: list[str]) -> None:
    """Пустой список — сброс override (NULL в БД)."""
    if not shops:
        db.execute(
            text(
                f"UPDATE {qname('users')} SET allowed_shops = NULL, updated_at = now() "
                "WHERE id = CAST(:uid AS uuid)"
            ),
            {"uid": str(user_id)},
        )
        return
    payload = json.dumps(shops, ensure_ascii=False)
    db.execute(
        text(
            f"UPDATE {qname('users')} SET allowed_shops = :p, updated_at = now() "
            "WHERE id = CAST(:uid AS uuid)"
        ),
        {"uid": str(user_id), "p": payload},
    )


def fetch_all_tenant_shop_labels(db: Session, user_id: UUID | str) -> list[str]:
    """Те же метки, что и в подсказке админки (объединение storage / staging / dim_shop)."""
    uid = str(user_id)
    rows = db.execute(
        text(
            f"""
            WITH src AS (
                SELECT NULLIF(TRIM(fss.shop_raw), '') AS shop_name
                FROM {qname('fact_storage_snapshot')} fss
                WHERE fss.user_id = CAST(:uid AS uuid)
                UNION ALL
                SELECT NULLIF(TRIM(ss.shop_raw), '') AS shop_name
                FROM {qname('stg_storage')} ss
                WHERE ss.user_id = CAST(:uid AS uuid)
                UNION ALL
                SELECT NULLIF(TRIM(ds.shop_name), '') AS shop_name
                FROM {qname('dim_shop')} ds
                WHERE ds.user_id = CAST(:uid AS uuid)
            ),
            cleaned AS (
                SELECT shop_name
                FROM src
                WHERE shop_name IS NOT NULL
                  AND shop_name <> ''
                  AND lower(shop_name) NOT IN ({UNDEFINED_SHOP_SQL_LIST})
            ),
            norm AS (
                SELECT
                    upper(regexp_replace(trim(shop_name), '\\s+', ' ', 'g')) AS shop_norm,
                    MIN(shop_name) AS label
                FROM cleaned
                GROUP BY 1
            )
            SELECT label
            FROM norm
            ORDER BY shop_norm
            """
        ),
        {"uid": uid},
    ).fetchall()
    return [str(r[0]) for r in rows or [] if r and r[0]]


def canonicalize_allowlist(selection: list[str], all_labels: list[str]) -> list[str]:
    """Подбирает канонические подписи из all_labels по нормализации."""
    by_norm = {norm_shop_label(l): l for l in all_labels}
    out: list[str] = []
    seen: set[str] = set()
    for s in selection:
        n = norm_shop_label(s)
        if not n:
            continue
        canon = by_norm.get(n)
        if canon is None:
            raise ValueError(f"Unknown shop: {s!r}")
        cn = norm_shop_label(canon)
        if cn not in seen:
            out.append(canon)
            seen.add(cn)
    return out
