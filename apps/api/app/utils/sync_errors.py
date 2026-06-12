"""Short summaries vs full text for Uzum sync log errors."""

from __future__ import annotations

import re

SUMMARY_MAX_LEN = 300


def split_sync_error(raw: str | None) -> tuple[str | None, str | None]:
    """Split raw exception into (short_summary, full_detail) for sync logs."""
    if not raw or not str(raw).strip():
        return None, None

    full = str(raw).strip()
    summary = full.split("\n")[0]

    pg_match = re.search(r"\(psycopg2\.errors\.(\w+)\)\s*([^\n\[]+)", full)
    if pg_match:
        pg_type, pg_msg = pg_match.group(1), pg_match.group(2).strip()
        hint_match = re.search(r"HINT:\s*([^\n]+)", full)
        hint = hint_match.group(1).strip() if hint_match else None

        prefix_match = re.match(r"(Error [^:]+:)", full)
        prefix = prefix_match.group(1) if prefix_match else None

        if prefix:
            summary = f"{prefix} {pg_msg}"
        else:
            summary = pg_msg

        if hint and pg_type == "CardinalityViolation":
            summary = f"{summary} — {hint}"

    if len(summary) > SUMMARY_MAX_LEN:
        summary = summary[: SUMMARY_MAX_LEN - 1] + "…"

    return summary, full
