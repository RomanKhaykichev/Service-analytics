"""Read-only Profiboard unit COGS lookups (no DDL on hot path)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import qname


def _table_exists(db: Session, full_name: str) -> bool:
    try:
        return db.execute(
            text("SELECT to_regclass(:t) IS NOT NULL"),
            {"t": full_name},
        ).scalar() is True
    except Exception:
        return False


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def load_latest_profiboard_by_barcode(db: Session, user_id: UUID) -> dict[str, dict]:
    """Последняя запись Profiboard по каждому штрихкоду (max effective_from)."""
    latest: dict[str, dict] = {}

    def _consider(bn: str, eff_raw, cogs_raw) -> None:
        if not bn or eff_raw is None:
            return
        eff_str = eff_raw.isoformat() if hasattr(eff_raw, "isoformat") else str(eff_raw).strip()
        if not eff_str:
            return
        cogs_val = _safe_float(cogs_raw)
        if cogs_val is None:
            return
        prev = latest.get(bn)
        if prev is None or eff_str > prev["effective_from"]:
            latest[bn] = {"cogs": cogs_val, "effective_from": eff_str}

    hist_tbl = qname("manual_product_cogs_history")
    if _table_exists(db, hist_tbl):
        for row in db.execute(
            text(f"""
                SELECT DISTINCT ON (barcode_norm)
                    barcode_norm, effective_from, cogs_sum
                FROM {hist_tbl}
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY barcode_norm, effective_from DESC, created_at DESC
            """),
            {"user_id": str(user_id)},
        ).fetchall():
            bn = (row[0] or "").strip()
            _consider(bn, row[1], row[2])

    manual_tbl = qname("manual_product_cogs")
    if _table_exists(db, manual_tbl):
        for row in db.execute(
            text(f"""
                SELECT barcode_norm, effective_from, cogs_sum
                FROM {manual_tbl}
                WHERE user_id = CAST(:user_id AS uuid)
                  AND effective_from IS NOT NULL
            """),
            {"user_id": str(user_id)},
        ).fetchall():
            bn = (row[0] or "").strip()
            _consider(bn, row[1], row[2])

    return latest
