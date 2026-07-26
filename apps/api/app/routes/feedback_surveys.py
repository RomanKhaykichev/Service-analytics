"""
Опросник обратной связи: отправка пользователем и список для админки.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, qname
from app.deps import require_admin, require_user
from app.settings import get_settings

router = APIRouter()


def _ensure_feedback_surveys_resolved_column(db: Session) -> None:
    schema = get_settings().DB_SCHEMA
    r = db.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'feedback_surveys' AND column_name = 'resolved'
            """
        ),
        {"s": schema},
    ).fetchone()
    if r:
        return
    db.execute(
        text(
            f"""
            ALTER TABLE {qname("feedback_surveys")}
            ADD COLUMN IF NOT EXISTS resolved boolean NOT NULL DEFAULT false
            """
        )
    )


def _ensure_feedback_surveys_table(db: Session) -> None:
    schema = get_settings().DB_SCHEMA
    r = db.execute(
        text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :s AND table_name = 'feedback_surveys'
            """
        ),
        {"s": schema},
    ).fetchone()
    if not r:
        users = f"{schema}.users"
        tbl = f"{schema}.feedback_surveys"
        db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL REFERENCES {users}(id) ON DELETE CASCADE,
                    answers jsonb NOT NULL,
                    nps smallint,
                    helpfulness smallint,
                    client_name varchar(255),
                    client_contact varchar(255),
                    created_at timestamptz NOT NULL DEFAULT now(),
                    resolved boolean NOT NULL DEFAULT false
                )
                """
            )
        )
        db.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_feedback_surveys_created_at ON {tbl} (created_at DESC)")
        )
        db.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_feedback_surveys_user_id ON {tbl} (user_id)")
        )
    _ensure_feedback_surveys_resolved_column(db)


class FeedbackSurveyCreate(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    nps: Optional[int] = Field(default=None, ge=0, le=10)
    helpfulness: Optional[int] = Field(default=None, ge=1, le=10)
    client_name: Optional[str] = Field(default=None, max_length=255)
    client_contact: Optional[str] = Field(default=None, max_length=255)


class FeedbackSurveyCreateResponse(BaseModel):
    id: str
    created_at: str


class FeedbackSurveyAdminRow(BaseModel):
    id: str
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    answers: dict[str, Any]
    nps: Optional[int] = None
    helpfulness: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    created_at: str
    resolved: bool = False


class FeedbackSurveysAdminListResponse(BaseModel):
    surveys: list[FeedbackSurveyAdminRow]
    total_count: int


class FeedbackSurveyAdminPatch(BaseModel):
    resolved: bool


def _dt_iso(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value) if value else ""


def _parse_answers(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"raw": parsed}
        except Exception:
            return {"raw": raw}
    return {}


def _row_to_admin(r) -> FeedbackSurveyAdminRow:
    return FeedbackSurveyAdminRow(
        id=str(r[0]),
        user_id=str(r[1]),
        answers=_parse_answers(r[2]),
        nps=int(r[3]) if r[3] is not None else None,
        helpfulness=int(r[4]) if r[4] is not None else None,
        client_name=r[5],
        client_contact=r[6],
        created_at=_dt_iso(r[7]),
        resolved=bool(r[8]) if r[8] is not None else False,
        email=r[9],
        full_name=r[10],
    )


_ADMIN_SELECT = """
            SELECT
                s.id,
                s.user_id,
                s.answers,
                s.nps,
                s.helpfulness,
                s.client_name,
                s.client_contact,
                s.created_at,
                COALESCE(s.resolved, false) AS resolved,
                u.email,
                u.full_name
            FROM {tbl} s
            LEFT JOIN {users} u ON u.id = s.user_id
"""


@router.post("/feedback/surveys", response_model=FeedbackSurveyCreateResponse)
async def create_feedback_survey(
    body: FeedbackSurveyCreate,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not body.answers:
        raise HTTPException(status_code=422, detail="Answers are required")

    _ensure_feedback_surveys_table(db)

    client_name = (body.client_name or "").strip() or None
    client_contact = (body.client_contact or "").strip() or None
    answers_json = json.dumps(body.answers, ensure_ascii=False)

    row = db.execute(
        text(
            f"""
            INSERT INTO {qname("feedback_surveys")}
                (user_id, answers, nps, helpfulness, client_name, client_contact)
            VALUES
                (
                    CAST(:uid AS uuid),
                    CAST(:answers AS jsonb),
                    :nps,
                    :helpfulness,
                    :client_name,
                    :client_contact
                )
            RETURNING id, created_at
            """
        ),
        {
            "uid": str(user_id),
            "answers": answers_json,
            "nps": body.nps,
            "helpfulness": body.helpfulness,
            "client_name": client_name,
            "client_contact": client_contact,
        },
    ).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create survey")
    db.commit()
    return FeedbackSurveyCreateResponse(id=str(row[0]), created_at=_dt_iso(row[1]))


@router.get("/admin/feedback-surveys", response_model=FeedbackSurveysAdminListResponse)
async def admin_list_feedback_surveys(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str = Query(
        "all",
        description="Фильтр: all — все, open — не закрытые (resolved=false), closed — закрытые (resolved=true)",
    ),
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_feedback_surveys_table(db)

    st = (status or "all").strip().lower()
    if st not in ("all", "open", "closed"):
        raise HTTPException(status_code=422, detail="status must be all, open, or closed")
    where_extra = ""
    if st == "open":
        where_extra = " AND (COALESCE(s.resolved, false) = false)"
    elif st == "closed":
        where_extra = " AND (COALESCE(s.resolved, false) = true)"

    offset = (page - 1) * page_size
    total = db.execute(
        text(f"SELECT COUNT(*) FROM {qname('feedback_surveys')} s WHERE 1=1 {where_extra}")
    ).scalar()
    total = int(total or 0)

    rows = db.execute(
        text(
            _ADMIN_SELECT.format(tbl=qname("feedback_surveys"), users=qname("users"))
            + f"""
            WHERE 1=1 {where_extra}
            ORDER BY s.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).fetchall()

    surveys = [_row_to_admin(r) for r in rows]
    return FeedbackSurveysAdminListResponse(surveys=surveys, total_count=total)


@router.patch("/admin/feedback-surveys/{survey_id}", response_model=FeedbackSurveyAdminRow)
async def admin_patch_feedback_survey(
    survey_id: UUID,
    body: FeedbackSurveyAdminPatch,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_feedback_surveys_table(db)
    res = db.execute(
        text(
            f"""
            UPDATE {qname("feedback_surveys")}
            SET resolved = CAST(:resolved AS boolean)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"resolved": body.resolved, "id": str(survey_id)},
    )
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Survey not found")
    db.commit()

    row = db.execute(
        text(
            _ADMIN_SELECT.format(tbl=qname("feedback_surveys"), users=qname("users"))
            + " WHERE s.id = CAST(:id AS uuid)"
        ),
        {"id": str(survey_id)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Survey not found")
    return _row_to_admin(row)


@router.delete("/admin/feedback-surveys/{survey_id}")
async def admin_delete_feedback_survey(
    survey_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_feedback_surveys_table(db)
    res = db.execute(
        text(f"DELETE FROM {qname('feedback_surveys')} WHERE id = CAST(:id AS uuid)"),
        {"id": str(survey_id)},
    )
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Survey not found")
    db.commit()
    return {"ok": True}
