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

_EXCLUDED_SHOP_LABELS = frozenset(
    s.lower()
    for s in (
        "не определено",
        "неопределено",
        "undefined",
        "null",
        "(не определено)",
        "не определен",
        "(Не определено)",
    )
)


def is_valid_shop_label(name: str) -> bool:
    s = str(name).strip()
    return bool(s) and s.lower() not in _EXCLUDED_SHOP_LABELS


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


def _shop_labels_union_sql() -> str:
    """Объединение всех витринных названий магазинов пользователя из отчётов и dim_shop."""
    return f"""
            WITH src AS (
                SELECT NULLIF(TRIM(fss.shop_raw), '') AS shop_name
                FROM {qname('fact_storage_snapshot')} fss
                WHERE fss.user_id = CAST(:uid AS uuid)
                UNION ALL
                SELECT NULLIF(TRIM(ss.shop_raw), '') AS shop_name
                FROM {qname('stg_storage')} ss
                WHERE ss.user_id = CAST(:uid AS uuid)
                UNION ALL
                SELECT NULLIF(TRIM(ds2.shop_name), '') AS shop_name
                FROM {qname('fact_leftout_snapshot')} fl
                JOIN {qname('dim_shop')} ds2
                  ON ds2.shop_id = fl.shop_id AND ds2.user_id = fl.user_id
                WHERE fl.user_id = CAST(:uid AS uuid)
                UNION ALL
                SELECT NULLIF(TRIM(sl.shop_raw), '') AS shop_name
                FROM {qname('stg_leftout')} sl
                WHERE sl.user_id = CAST(:uid AS uuid)
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
    """


def merge_shop_labels(*lists: list[str]) -> list[str]:
    """Дедупликация по нормализованному названию, порядок — по shop_norm."""
    merged: dict[str, str] = {}
    for lst in lists:
        for raw in lst:
            if not is_valid_shop_label(raw):
                continue
            label = str(raw).strip()
            merged.setdefault(norm_shop_label(label), label)
    return [merged[k] for k in sorted(merged.keys())]


def upsert_dim_shop_names(db: Session, user_id: UUID | str, shop_names: list[str]) -> None:
    """Сохраняет все встреченные названия магазинов (в т.ч. до фильтра по тарифу)."""
    ensure_dim_shop_uzum_columns(db)
    uid = str(user_id)
    seen: set[str] = set()
    for raw in shop_names:
        if not is_valid_shop_label(raw):
            continue
        label = str(raw).strip()
        n = norm_shop_label(label)
        if n in seen:
            continue
        seen.add(n)
        db.execute(
            text(
                f"""
                INSERT INTO {qname('dim_shop')} (user_id, shop_name)
                VALUES (CAST(:uid AS uuid), :shop_name)
                ON CONFLICT (user_id, shop_name) DO NOTHING
                """
            ),
            {"uid": uid, "shop_name": label},
        )


def ensure_dim_shop_uzum_columns(db: Session) -> None:
    """uzum_shop_id + api_key_accessible — разделение «в аккаунте» / «доступно ключу»."""
    for stmt in (
        f"ALTER TABLE {qname('dim_shop')} ADD COLUMN IF NOT EXISTS uzum_shop_id INTEGER",
        f"ALTER TABLE {qname('dim_shop')} "
        f"ADD COLUMN IF NOT EXISTS api_key_accessible BOOLEAN NOT NULL DEFAULT false",
    ):
        db.execute(text(stmt))


def register_uzum_api_dim_shops(
    db: Session,
    user_id: UUID | str,
    shops: list[dict],
    accessible_shop_ids: set[int],
) -> None:
    """
    Все магазины из /v1/shops в dim_shop; api_key_accessible=true только для доступных ключу.
    """
    ensure_dim_shop_uzum_columns(db)
    uid = str(user_id)
    uzum_ids_in_response: list[int] = []

    for shop in shops:
        if not isinstance(shop, dict):
            continue
        raw_id = shop.get("id")
        name = str(shop.get("name") or "").strip()
        if raw_id is None or not is_valid_shop_label(name):
            continue
        try:
            uzum_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        uzum_ids_in_response.append(uzum_id)
        accessible = uzum_id in accessible_shop_ids
        db.execute(
            text(
                f"""
                INSERT INTO {qname('dim_shop')} (
                    user_id, shop_name, uzum_shop_id, api_key_accessible
                )
                VALUES (
                    CAST(:uid AS uuid), :shop_name, :uzum_shop_id, :accessible
                )
                ON CONFLICT (user_id, shop_name) DO UPDATE SET
                    uzum_shop_id = EXCLUDED.uzum_shop_id,
                    api_key_accessible = EXCLUDED.api_key_accessible
                """
            ),
            {
                "uid": uid,
                "shop_name": name,
                "uzum_shop_id": uzum_id,
                "accessible": accessible,
            },
        )

    if uzum_ids_in_response:
        db.execute(
            text(
                f"""
                UPDATE {qname('dim_shop')}
                SET api_key_accessible = false
                WHERE user_id = CAST(:uid AS uuid)
                  AND uzum_shop_id IS NOT NULL
                  AND uzum_shop_id = ANY(:uzum_ids)
                  AND NOT (uzum_shop_id = ANY(:accessible_ids))
                """
            ),
            {
                "uid": uid,
                "uzum_ids": uzum_ids_in_response,
                "accessible_ids": list(accessible_shop_ids),
            },
        )


def fetch_api_accessible_shop_labels(db: Session, user_id: UUID | str) -> list[str]:
    """Магазины dim_shop, помеченные как доступные текущему API-ключу."""
    ensure_dim_shop_uzum_columns(db)
    uid = str(user_id)
    rows = db.execute(
        text(
            f"""
            SELECT shop_name
            FROM {qname('dim_shop')}
            WHERE user_id = CAST(:uid AS uuid)
              AND api_key_accessible = true
              AND shop_name IS NOT NULL
              AND TRIM(shop_name) <> ''
            ORDER BY shop_name
            """
        ),
        {"uid": uid},
    ).fetchall()
    return [str(r[0]) for r in rows or [] if r and r[0]]


def fetch_all_tenant_shop_labels(db: Session, user_id: UUID | str) -> list[str]:
    """Все загруженные магазины пользователя (отчёты + dim_shop)."""
    uid = str(user_id)
    rows = db.execute(
        text(
            f"""
            {_shop_labels_union_sql()}
            SELECT label
            FROM norm
            ORDER BY shop_norm
            """
        ),
        {"uid": uid},
    ).fetchall()
    return [str(r[0]) for r in rows or [] if r and r[0]]


def count_tenant_shop_labels(db: Session, user_id: UUID | str) -> int:
    """Количество уникальных магазинов пользователя для колонки «Магазин» в админке."""
    uid = str(user_id)
    row = db.execute(
        text(
            f"""
            {_shop_labels_union_sql()}
            SELECT COUNT(*) FROM norm
            """
        ),
        {"uid": uid},
    ).fetchone()
    return int(row[0] or 0) if row else 0


def resolve_allowed_shop_labels(
    db: Session,
    user_id: UUID,
    all_labels: list[str],
    *,
    max_shops: Optional[int],
) -> tuple[list[str], Optional[str]]:
    """
    Разрешённые магазины для подсветки в админке.
    Возвращает (allowed_labels, active_shop).
    """
    undefined_list = UNDEFINED_SHOP_SQL_LIST
    uid = str(user_id)
    label_by_norm = {norm_shop_label(lbl): lbl for lbl in all_labels}

    override = get_user_allowed_shops_list(db, user_id)
    if override:
        allowed: list[str] = []
        for o in override:
            n = norm_shop_label(o)
            if not n:
                continue
            canon = label_by_norm.get(n, str(o).strip())
            if is_valid_shop_label(canon):
                allowed.append(canon)
        active = allowed[0] if allowed else None
        return allowed, active

    limit_sql = "" if max_shops is None else f" LIMIT {int(max_shops)}"
    rows_allowed = db.execute(
        text(
            f"""
            SELECT shop_name
            FROM {qname('dim_shop')}
            WHERE user_id = :uid
              AND shop_name IS NOT NULL
              AND TRIM(shop_name) <> ''
              AND lower(TRIM(shop_name)) NOT IN ({undefined_list})
            ORDER BY shop_name
            {limit_sql}
            """
        ),
        {"uid": uid},
    ).fetchall()
    allowed = [str(r[0]) for r in rows_allowed or []]
    active = allowed[0] if allowed else None
    return allowed, active


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
