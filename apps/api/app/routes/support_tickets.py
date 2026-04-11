"""
Обращения в поддержку: создание пользователем и список для админки.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, qname
from app.deps import require_admin, require_user
from app.settings import get_settings

router = APIRouter()


def _ensure_support_tickets_resolved_column(db: Session) -> None:
    schema = get_settings().DB_SCHEMA
    r = db.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'support_tickets' AND column_name = 'resolved'
            """
        ),
        {"s": schema},
    ).fetchone()
    if r:
        return
    db.execute(
        text(
            f"""
            ALTER TABLE {qname("support_tickets")}
            ADD COLUMN IF NOT EXISTS resolved boolean NOT NULL DEFAULT false
            """
        )
    )


def _ensure_support_tickets_table(db: Session) -> None:
    """
    Создаёт app.support_tickets, если её нет (удобно, когда миграции крутили в другую БД,
    чем та, куда смотрит запущенный uvicorn).
    """
    schema = get_settings().DB_SCHEMA
    r = db.execute(
        text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :s AND table_name = 'support_tickets'
            """
        ),
        {"s": schema},
    ).fetchone()
    if not r:
        users = f"{schema}.users"
        tbl = f"{schema}.support_tickets"
        db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL REFERENCES {users}(id) ON DELETE CASCADE,
                    subject varchar(500) NOT NULL,
                    priority varchar(32) NOT NULL DEFAULT 'medium',
                    category varchar(64) NOT NULL,
                    description text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    resolved boolean NOT NULL DEFAULT false
                )
                """
            )
        )
        db.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_support_tickets_created_at ON {tbl} (created_at DESC)"
            )
        )
        db.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_support_tickets_user_id ON {tbl} (user_id)"
            )
        )
    _ensure_support_tickets_resolved_column(db)


PRIORITIES = frozenset({"low", "medium", "high", "critical"})
CATEGORIES = frozenset({"technical", "billing", "feature", "data", "other"})


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    priority: str = Field(default="medium")
    category: str = Field(default="technical")
    description: str = Field(..., min_length=1, max_length=20000)


class SupportTicketCreateResponse(BaseModel):
    id: str
    created_at: str


class SupportTicketAdminRow(BaseModel):
    id: str
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    subject: str
    priority: str
    category: str
    description: str
    created_at: str
    resolved: bool = False


class SupportTicketsAdminListResponse(BaseModel):
    tickets: list[SupportTicketAdminRow]
    total_count: int


class SupportTicketAdminPatch(BaseModel):
    resolved: bool


def _normalize_priority(p: str) -> str:
    v = (p or "medium").strip().lower()
    if v not in PRIORITIES:
        raise HTTPException(status_code=422, detail="Invalid priority")
    return v


def _normalize_category(c: str) -> str:
    v = (c or "other").strip().lower()
    if v not in CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid category")
    return v


@router.post("/support/tickets", response_model=SupportTicketCreateResponse)
async def create_support_ticket(
    body: SupportTicketCreate,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    priority = _normalize_priority(body.priority)
    category = _normalize_category(body.category)
    subject = body.subject.strip()
    description = body.description.strip()
    if not subject:
        raise HTTPException(status_code=422, detail="Subject is required")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")

    _ensure_support_tickets_table(db)

    row = db.execute(
        text(
            f"""
            INSERT INTO {qname("support_tickets")}
                (user_id, subject, priority, category, description)
            VALUES
                (CAST(:uid AS uuid), :subject, :priority, :category, :description)
            RETURNING id, created_at
            """
        ),
        {
            "uid": str(user_id),
            "subject": subject,
            "priority": priority,
            "category": category,
            "description": description,
        },
    ).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create ticket")
    db.commit()
    tid, created_at = row[0], row[1]
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_iso = created_at.isoformat()
    else:
        created_iso = str(created_at)
    return SupportTicketCreateResponse(id=str(tid), created_at=created_iso)


@router.get("/admin/support-tickets", response_model=SupportTicketsAdminListResponse)
async def admin_list_support_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str = Query(
        "all",
        description="Фильтр: all — все, open — не закрытые (resolved=false), closed — закрытые (resolved=true)",
    ),
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_support_tickets_table(db)

    st = (status or "all").strip().lower()
    if st not in ("all", "open", "closed"):
        raise HTTPException(status_code=422, detail="status must be all, open, or closed")
    where_extra = ""
    if st == "open":
        where_extra = " AND (COALESCE(t.resolved, false) = false)"
    elif st == "closed":
        where_extra = " AND (COALESCE(t.resolved, false) = true)"

    offset = (page - 1) * page_size
    total = db.execute(
        text(
            f"SELECT COUNT(*) FROM {qname('support_tickets')} t WHERE 1=1 {where_extra}"
        )
    ).scalar()
    total = int(total or 0)

    rows = db.execute(
        text(
            f"""
            SELECT
                t.id,
                t.user_id,
                t.subject,
                t.priority,
                t.category,
                t.description,
                t.created_at,
                COALESCE(t.resolved, false) AS resolved,
                u.email,
                u.full_name
            FROM {qname("support_tickets")} t
            LEFT JOIN {qname("users")} u ON u.id = t.user_id
            WHERE 1=1 {where_extra}
            ORDER BY t.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).fetchall()

    tickets: list[SupportTicketAdminRow] = []
    for r in rows:
        created_at = r[6]
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            created_iso = created_at.isoformat()
        else:
            created_iso = str(created_at) if created_at else ""
        resolved_val = bool(r[7]) if r[7] is not None else False
        tickets.append(
            SupportTicketAdminRow(
                id=str(r[0]),
                user_id=str(r[1]),
                subject=r[2] or "",
                priority=r[3] or "",
                category=r[4] or "",
                description=r[5] or "",
                created_at=created_iso,
                resolved=resolved_val,
                email=r[8],
                full_name=r[9],
            )
        )
    return SupportTicketsAdminListResponse(tickets=tickets, total_count=total)


@router.patch("/admin/support-tickets/{ticket_id}", response_model=SupportTicketAdminRow)
async def admin_patch_support_ticket(
    ticket_id: UUID,
    body: SupportTicketAdminPatch,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_support_tickets_table(db)
    res = db.execute(
        text(
            f"""
            UPDATE {qname("support_tickets")}
            SET resolved = CAST(:resolved AS boolean)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"resolved": body.resolved, "id": str(ticket_id)},
    )
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.commit()

    row = db.execute(
        text(
            f"""
            SELECT
                t.id,
                t.user_id,
                t.subject,
                t.priority,
                t.category,
                t.description,
                t.created_at,
                COALESCE(t.resolved, false) AS resolved,
                u.email,
                u.full_name
            FROM {qname("support_tickets")} t
            LEFT JOIN {qname("users")} u ON u.id = t.user_id
            WHERE t.id = CAST(:id AS uuid)
            """
        ),
        {"id": str(ticket_id)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    created_at = row[6]
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_iso = created_at.isoformat()
    else:
        created_iso = str(created_at) if created_at else ""
    return SupportTicketAdminRow(
        id=str(row[0]),
        user_id=str(row[1]),
        subject=row[2] or "",
        priority=row[3] or "",
        category=row[4] or "",
        description=row[5] or "",
        created_at=created_iso,
        resolved=bool(row[7]) if row[7] is not None else False,
        email=row[8],
        full_name=row[9],
    )


@router.delete("/admin/support-tickets/{ticket_id}")
async def admin_delete_support_ticket(
    ticket_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_support_tickets_table(db)
    res = db.execute(
        text(f"DELETE FROM {qname('support_tickets')} WHERE id = CAST(:id AS uuid)"),
        {"id": str(ticket_id)},
    )
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.commit()
    return {"ok": True}
