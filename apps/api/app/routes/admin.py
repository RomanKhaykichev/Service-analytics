"""
Admin-only API: overview KPIs, tenants list/detail, tenant actions.
All routes require ADMIN_USER_IDS (env) and valid admin user (JWT).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Any
from pydantic import BaseModel
import logging

from app.db import get_db, qname
from app.deps import require_admin
from app.settings import get_settings
from app.auth import hash_password
from app.models import User, RefreshToken

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# --- Response models ---

class AdminOverviewKPIs(BaseModel):
    active_customers_mau_30d: Optional[int] = None
    new_signups_7d: Optional[int] = None
    new_signups_30d: Optional[int] = None
    activated_pct: Optional[float] = None  # % signup -> first import
    paid_count: Optional[int] = None
    trial_count: Optional[int] = None
    expired_count: Optional[int] = None
    mrr: Optional[float] = None
    revenue_30d: Optional[float] = None
    imports_24h: Optional[int] = None
    import_success_rate_7d: Optional[float] = None
    queue_pending: Optional[int] = None
    queue_running: Optional[int] = None
    queue_failed: Optional[int] = None
    oldest_pending_minutes: Optional[float] = None
    api_errors_5xx_24h: Optional[int] = None


class RegistrationsPerDayPoint(BaseModel):
    date: str
    count: int


class ImportsPerDayPoint(BaseModel):
    date: str
    success: int
    failed: int


class DataFreshnessBucket(BaseModel):
    bucket: str  # "0-3" | "4-7" | "8-14" | "15+"
    count: int


class SubscriptionAnalyticsPoint(BaseModel):
    month: str  # "YYYY-MM"
    active_users: int
    revenue: float


class AdminOverviewResponse(BaseModel):
    kpis: AdminOverviewKPIs
    registrations_per_day: list[RegistrationsPerDayPoint]
    visits_per_day: list[RegistrationsPerDayPoint]  # уникальные пользователи, заходившие в этот день (last_login_at)
    total_visits_per_day: list[RegistrationsPerDayPoint] = []  # Посещения: общее количество заходов по дням (login_events)
    imports_per_day: list[ImportsPerDayPoint]
    import_processing_p50_p95: Optional[list[dict]] = None  # [{date, p50, p95}]
    top_import_error_types: list[dict]  # [{error_type, count}]
    data_freshness_buckets: list[DataFreshnessBucket]
    subscription_analytics: list[SubscriptionAnalyticsPoint] = []  # по месяцам: активные пользователи, доход


class TenantRow(BaseModel):
    tenant_id: str
    company_name: Optional[str] = None
    owner_email: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[str] = None
    plan: str
    trial_ends_at: Optional[str] = None
    next_billing_date: Optional[str] = None
    payment_status: Optional[str] = None
    last_activity_at: Optional[str] = None
    last_import_at: Optional[str] = None
    last_import_status: Optional[str] = None
    last_import_type: Optional[str] = None
    data_freshness_days: Optional[int] = None
    imports_30d: int
    failed_imports_30d: int
    storage_mb: Optional[float] = None
    top_last_error: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    # Доп. колонки для таблицы
    shops_count: int = 0
    status: str = "active"  # active | blocked
    trial_days_left: Optional[int] = None
    paid: bool = False
    paid_amount: Optional[float] = None  # Оплачено — сумма, которую оплатил клиент
    last_login_at: Optional[str] = None  # дата последнего входа


class TenantShopsResponse(BaseModel):
    tenant_id: str
    shops: list[str] = []

class DashboardFunnel(BaseModel):
    visited_site: int  # Зашли на сайт — количество человек, зашедших на сайт (лендинг)
    tried: int  # Попробовали — количество нажатий «Попробовать бесплатно» в промо-окне
    registered: int  # Зарегистрировали
    paid: int  # Оплатили (план paid или кол-во оплат — здесь кол-во пользователей на платной подписке)
    conversion_pct: float  # Конверсия % (paid/registered*100)


class DashboardFiles(BaseModel):
    total: int  # Всего загружено файлов
    errors: int  # Из них ошибок
    error_pct: float  # Процент ошибки


class DashboardTotals(BaseModel):
    registered: int  # Всего зарегистрировано
    paid_subscription: int  # Платная подписка (пользователей)
    inactive_30d: int  # Неактивны более 30 дней: не заходили 30+ дней (по колонке last_login_at в users)


class MonthlyRow(BaseModel):
    month: str  # "YYYY-MM"
    month_label: str  # "Фев 2026"
    profit: float  # Прибыль (сумма оплат за месяц)
    registrations: int
    payments: int  # Количество оплат (операций)
    active_users: int  # Подписчики: кол-во аккаунтов с тарифом Month 5 и Month 10, оплативших в этом месяце


class DashboardMetricsResponse(BaseModel):
    funnel: DashboardFunnel
    files: DashboardFiles
    totals: DashboardTotals
    monthly: list[MonthlyRow]


class TenantsListResponse(BaseModel):
    tenants: list[TenantRow]
    total_count: int


class TenantDetailResponse(BaseModel):
    tenant_id: str
    company_name: Optional[str] = None
    owner_email: Optional[str] = None
    created_at: Optional[str] = None
    plan: str
    trial_ends_at: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    last_import_at: Optional[str] = None
    last_import_batch_id: Optional[str] = None
    last_import_status: Optional[str] = None
    data_freshness_days: Optional[int] = None
    imports_30d: int
    failed_imports_30d: int


def _safe_date(r: Any, idx: int) -> Optional[str]:
    v = r[idx] if r and len(r) > idx else None
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)
    return str(v)[:10]


def _safe_ts(r: Any, idx: int) -> Optional[str]:
    v = r[idx] if r and len(r) > idx else None
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


@router.get("/admin/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    subscription_period: Optional[str] = Query("month", description="Аналитика подписок: day | week | month"),
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """KPI cards + chart data for admin dashboard. Uses upload_batch.created_at and users."""
    schema = settings.DB_SCHEMA
    to_d = to_date or date.today()
    from_d = from_date or (to_d - timedelta(days=90))
    if from_d > to_d:
        from_d, to_d = to_d, from_d
    sub_period = (subscription_period or "month").lower()
    if sub_period not in ("day", "week", "month"):
        sub_period = "month"

    kpis = AdminOverviewKPIs()
    now = datetime.now(timezone.utc)
    today = now.date()
    d30 = today - timedelta(days=30)
    d7 = today - timedelta(days=7)
    d1 = now - timedelta(hours=24)

    try:
        # upload_batch may not have created_at if migration not run
        has_created_at = False
        try:
            r = db.execute(text(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :s AND table_name = 'upload_batch' AND column_name = 'created_at'
            """), {"s": schema}).fetchone()
            has_created_at = r is not None
        except Exception:
            pass

        has_import_file_attempts = False
        try:
            r = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :s AND table_name = 'import_file_attempts'
            """), {"s": schema}).fetchone()
            has_import_file_attempts = r is not None
        except Exception:
            pass

        if has_created_at:
            # Active customers (MAU 30d): distinct users with upload_batch in last 30d
            r = db.execute(text(f"""
                SELECT COUNT(DISTINCT user_id) FROM {qname('upload_batch')}
                WHERE created_at >= :d30
            """), {"d30": d30}).fetchone()
            kpis.active_customers_mau_30d = r[0] if r else 0

            # Imports 24h
            r = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('upload_batch')}
                WHERE created_at >= :d1
            """), {"d1": d1}).fetchone()
            kpis.imports_24h = r[0] if r else 0

            # Import success rate 7d: по файлам (если есть import_file_attempts) или по батчам
            if has_import_file_attempts:
                r = db.execute(text(f"""
                    SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'success')
                    FROM {qname('import_file_attempts')}
                    WHERE created_at >= :d7
                """), {"d7": d7}).fetchone()
                total_7d = (r[0] or 0) if r else 0
                success_7d = (r[1] or 0) if r else 0
            else:
                r = db.execute(text(f"""
                    SELECT COUNT(DISTINCT b.upload_batch_id) FROM {qname('upload_batch')} b
                    WHERE b.created_at >= :d7
                """), {"d7": d7}).fetchone()
                total_7d = r[0] or 0
                r = db.execute(text(f"""
                    SELECT COUNT(DISTINCT b.upload_batch_id) FROM {qname('upload_batch')} b
                    WHERE b.created_at >= :d7
                      AND (EXISTS (SELECT 1 FROM {qname('fact_sales')} fs WHERE fs.user_id = b.user_id AND fs.upload_batch_id = b.upload_batch_id)
                           OR EXISTS (SELECT 1 FROM {qname('fact_expenses')} fe WHERE fe.user_id = b.user_id AND fe.upload_batch_id = b.upload_batch_id)
                           OR EXISTS (SELECT 1 FROM {qname('fact_leftout_snapshot')} fl WHERE fl.user_id = b.user_id AND fl.upload_batch_id = b.upload_batch_id)
                           OR EXISTS (SELECT 1 FROM {qname('fact_storage_snapshot')} fss WHERE fss.user_id = b.user_id AND fss.upload_batch_id = b.upload_batch_id)
                           OR EXISTS (SELECT 1 FROM {qname('fact_leftout_old_snapshot')} flo WHERE flo.user_id = b.user_id AND flo.upload_batch_id = b.upload_batch_id))
                """), {"d7": d7}).fetchone()
                success_7d = r[0] or 0
            kpis.import_success_rate_7d = (success_7d / total_7d * 100) if total_7d else None
        else:
            kpis.active_customers_mau_30d = None
            kpis.imports_24h = None
            kpis.import_success_rate_7d = None

        # New signups 7d / 30d
        r = db.execute(text(f"""
            SELECT COUNT(*) FROM {qname('users')} WHERE created_at >= :d7
        """), {"d7": d7}).fetchone()
        kpis.new_signups_7d = r[0] if r else 0
        r = db.execute(text(f"""
            SELECT COUNT(*) FROM {qname('users')} WHERE created_at >= :d30
        """), {"d30": d30}).fetchone()
        kpis.new_signups_30d = r[0] if r else 0

        # Activated %: users with at least one upload_batch / total users
        r = db.execute(text(f"SELECT COUNT(*) FROM {qname('users')}")).fetchone()
        total_users = r[0] or 0
        r = db.execute(text(f"""
            SELECT COUNT(DISTINCT user_id) FROM {qname('upload_batch')}
        """)).fetchone()
        users_with_import = r[0] or 0
        kpis.activated_pct = (users_with_import / total_users * 100) if total_users else None

        # Plan counts (users.plan, users.trial_ends_at)
        try:
            r = db.execute(text(f"""
                SELECT plan, trial_ends_at FROM {qname('users')}
            """)).fetchall()
            paid = trial = expired = 0
            for row in r or []:
                plan = (row[0] or "trial").lower()
                te = row[1]
                if plan == "paid":
                    paid += 1
                elif te and te < now:
                    expired += 1
                else:
                    trial += 1
            kpis.paid_count = paid
            kpis.trial_count = trial
            kpis.expired_count = expired
        except Exception:
            kpis.paid_count = kpis.trial_count = kpis.expired_count = None

        kpis.mrr = None
        kpis.revenue_30d = None
        kpis.queue_pending = 0
        kpis.queue_running = 0
        kpis.queue_failed = 0
        kpis.oldest_pending_minutes = None
        kpis.api_errors_5xx_24h = None

    except Exception as e:
        logger.warning(f"Admin overview KPIs partial failure: {e}")
        db.rollback()

    # Для графиков «Регистрации / заходы / посещения» всегда включаем сегодня (дата сервера)
    to_d_chart = to_d if to_d >= today else today
    # Registrations per day (включая полный день to_d — сегодня)
    registrations_per_day: list[RegistrationsPerDayPoint] = []
    try:
        rows = db.execute(text(f"""
            SELECT date_trunc('day', created_at)::date AS d, COUNT(*)
            FROM {qname('users')}
            WHERE created_at::date >= :from_d AND created_at::date <= :to_d
            GROUP BY 1 ORDER BY 1
        """), {"from_d": from_d, "to_d": to_d_chart}).fetchall()
        for row in rows or []:
            registrations_per_day.append(RegistrationsPerDayPoint(date=str(row[0])[:10], count=row[1]))
    except Exception as e:
        logger.warning(f"Admin registrations_per_day: {e}")
        db.rollback()

    # Visits per day (users who logged in that day, by last_login_at)
    visits_per_day: list[RegistrationsPerDayPoint] = []
    try:
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name = 'last_login_at'
        """), {"s": schema}).fetchone()
        if r:
            rows = db.execute(text(f"""
                SELECT date_trunc('day', last_login_at)::date AS d, COUNT(*)
                FROM {qname('users')}
                WHERE last_login_at::date >= :from_d AND last_login_at::date <= :to_d
                GROUP BY 1 ORDER BY 1
            """), {"from_d": from_d, "to_d": to_d_chart}).fetchall()
            for row in rows or []:
                visits_per_day.append(RegistrationsPerDayPoint(date=str(row[0])[:10], count=row[1]))
    except Exception as e:
        logger.warning(f"Admin visits_per_day: {e}")
        db.rollback()

    # Посещения: общее количество заходов по дням (из login_events)
    total_visits_per_day: list[RegistrationsPerDayPoint] = []
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :s AND table_name = 'login_events'
        """), {"s": schema}).fetchone()
        if not r:
            logger.info("Таблица login_events не найдена — выполните: alembic upgrade head (миграция 20260150)")
        else:
            # дата в UTC, чтобы совпадала с today на сервере
            rows = db.execute(text(f"""
                SELECT (date_trunc('day', logged_at AT TIME ZONE 'UTC'))::date AS d, COUNT(*)
                FROM {qname('login_events')}
                WHERE (logged_at AT TIME ZONE 'UTC')::date >= :from_d AND (logged_at AT TIME ZONE 'UTC')::date <= :to_d
                GROUP BY 1 ORDER BY 1
            """), {"from_d": from_d, "to_d": to_d_chart}).fetchall()
            for row in rows or []:
                total_visits_per_day.append(RegistrationsPerDayPoint(date=str(row[0])[:10], count=row[1]))
    except Exception as e:
        logger.warning("Admin total_visits_per_day (login_events): %s", e)
        db.rollback()

    # Imports per day: по каждому файлу — успех/ошибка (если есть import_file_attempts), иначе по батчам
    imports_per_day: list[ImportsPerDayPoint] = []
    if has_import_file_attempts:
        try:
            rows = db.execute(text(f"""
                SELECT date_trunc('day', created_at)::date AS d,
                       COUNT(*) FILTER (WHERE status = 'success') AS success,
                       COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM {qname('import_file_attempts')}
                WHERE created_at::date >= :from_d AND created_at::date <= :to_d
                GROUP BY 1 ORDER BY 1
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
            for row in rows or []:
                d = str(row[0])[:10]
                success = row[1] or 0
                failed = row[2] or 0
                imports_per_day.append(ImportsPerDayPoint(date=d, success=success, failed=failed))
        except Exception as e:
            logger.warning(f"Admin imports_per_day (attempts): {e}")
            db.rollback()
    elif has_created_at:
        try:
            rows = db.execute(text(f"""
                SELECT date_trunc('day', b.created_at)::date AS d,
                       COUNT(DISTINCT b.upload_batch_id) AS total,
                       COUNT(DISTINCT CASE WHEN (
                         EXISTS (SELECT 1 FROM {qname('fact_sales')} fs WHERE fs.user_id = b.user_id AND fs.upload_batch_id = b.upload_batch_id)
                         OR EXISTS (SELECT 1 FROM {qname('fact_expenses')} fe WHERE fe.user_id = b.user_id AND fe.upload_batch_id = b.upload_batch_id)
                         OR EXISTS (SELECT 1 FROM {qname('fact_leftout_snapshot')} fl WHERE fl.user_id = b.user_id AND fl.upload_batch_id = b.upload_batch_id)
                         OR EXISTS (SELECT 1 FROM {qname('fact_storage_snapshot')} fss WHERE fss.user_id = b.user_id AND fss.upload_batch_id = b.upload_batch_id)
                         OR EXISTS (SELECT 1 FROM {qname('fact_leftout_old_snapshot')} flo WHERE flo.user_id = b.user_id AND flo.upload_batch_id = b.upload_batch_id)
                       ) THEN b.upload_batch_id END) AS success
                FROM {qname('upload_batch')} b
                WHERE b.created_at::date >= :from_d AND b.created_at::date <= :to_d
                GROUP BY 1 ORDER BY 1
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
            for row in rows or []:
                d = str(row[0])[:10]
                total = row[1] or 0
                success = row[2] or 0
                failed = total - success
                imports_per_day.append(ImportsPerDayPoint(date=d, success=success, failed=failed))
        except Exception as e:
            logger.warning(f"Admin imports_per_day: {e}")
            db.rollback()

    # Top import error types: no table, return empty
    top_import_error_types: list[dict] = []

    # Data freshness buckets: by user, max(date_created) from fact_sales -> days ago
    data_freshness_buckets: list[DataFreshnessBucket] = []
    try:
        rows = db.execute(text(f"""
            WITH last_data AS (
                SELECT user_id, MAX(date_created)::date AS last_d
                FROM {qname('fact_sales')}
                GROUP BY user_id
            ),
            days_ago AS (
                SELECT user_id, (CAST(:today AS date) - last_d) AS d
                FROM last_data
            )
            SELECT
                COUNT(*) FILTER (WHERE d <= 3) AS b0_3,
                COUNT(*) FILTER (WHERE d >= 4 AND d <= 7) AS b4_7,
                COUNT(*) FILTER (WHERE d >= 8 AND d <= 14) AS b8_14,
                COUNT(*) FILTER (WHERE d >= 15) AS b15
            FROM days_ago
        """), {"today": today}).fetchone()
        if rows:
            data_freshness_buckets = [
                DataFreshnessBucket(bucket="0-3", count=rows[0] or 0),
                DataFreshnessBucket(bucket="4-7", count=rows[1] or 0),
                DataFreshnessBucket(bucket="8-14", count=rows[2] or 0),
                DataFreshnessBucket(bucket="15+", count=rows[3] or 0),
            ]
    except Exception as e:
        logger.warning(f"Admin data_freshness_buckets: {e}")
        db.rollback()

    # Аналитика подписок: по дням / неделям / месяцам — всегда до и включая сегодня
    subscription_analytics: list[SubscriptionAnalyticsPoint] = []
    try:
        db.rollback()  # сброс транзакции на случай сбоя в предыдущих блоках (data_freshness_buckets и т.д.)
        end_date = today  # всегда учитываем сегодняшний день, независимо от from/to
        periods: list[tuple[date, date, str]] = []  # (from_d, to_d, label)
        if sub_period == "day":
            # 30 дней: от (сегодня - 29) до сегодня включительно
            for i in range(29, -1, -1):
                d = end_date - timedelta(days=i)
                periods.append((d, d, d.strftime("%Y-%m-%d")))
        elif sub_period == "week":
            # 12 недель: последняя неделя заканчивается сегодня
            for i in range(11, -1, -1):
                end = end_date - timedelta(days=i * 7)
                start = end - timedelta(days=6)
                periods.append((start, end, start.strftime("%d.%m")))
        else:
            # month: последние 12 месяцев, текущий месяц — по сегодня
            d = date(end_date.year, end_date.month, 1)
            for _ in range(12):
                from_m = d.replace(day=1)
                if from_m.month == 12:
                    to_m = from_m.replace(year=from_m.year + 1, month=1) - timedelta(days=1)
                else:
                    to_m = from_m.replace(month=from_m.month + 1) - timedelta(days=1)
                if to_m > end_date:
                    to_m = end_date
                periods.append((from_m, to_m, from_m.strftime("%Y-%m")))
                d = from_m - timedelta(days=1)
            periods.reverse()
        has_last_login = False
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name = 'last_login_at'
        """), {"s": schema}).fetchone()
        if r:
            has_last_login = True
        for from_p, to_p, period_key in periods:
            active_users = 0
            if has_last_login:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT id) FROM {qname('users')}
                    WHERE last_login_at::date >= :from_p AND last_login_at::date <= :to_p AND is_active = true
                """), {"from_p": from_p, "to_p": to_p}).fetchone()
                active_users = r2[0] or 0 if r2 else 0
            else:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT user_id) FROM {qname('upload_batch')}
                    WHERE created_at::date >= :from_p AND created_at::date <= :to_p
                """), {"from_p": from_p, "to_p": to_p}).fetchone()
                active_users = r2[0] or 0 if r2 else 0
            revenue = 0.0
            try:
                r3 = db.execute(text(f"""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM {qname('user_payments')}
                    WHERE paid_at::date >= :from_p AND paid_at::date <= :to_p
                """), {"from_p": from_p, "to_p": to_p}).fetchone()
                revenue = float(r3[0] or 0) if r3 else 0.0
            except Exception:
                pass
            subscription_analytics.append(
                SubscriptionAnalyticsPoint(month=period_key, active_users=active_users, revenue=round(revenue, 2))
            )
    except Exception as e:
        logger.warning(f"Admin subscription_analytics: {e}")
        db.rollback()

    return AdminOverviewResponse(
        kpis=kpis,
        registrations_per_day=registrations_per_day,
        visits_per_day=visits_per_day,
        total_visits_per_day=total_visits_per_day,
        imports_per_day=imports_per_day,
        import_processing_p50_p95=None,
        top_import_error_types=top_import_error_types,
        data_freshness_buckets=data_freshness_buckets,
        subscription_analytics=subscription_analytics,
    )


# Месячные названия для метки (рус)
_MONTH_LABELS = (
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
)


def _parse_funnel_month(month_str: Optional[str]) -> Optional[tuple[date, date]]:
    """Parse YYYY-MM into (first_day, last_day) of month. Return None for «Общее»."""
    if not month_str or not month_str.strip():
        return None
    parts = month_str.strip().split("-")
    if len(parts) != 2:
        return None
    try:
        y, m = int(parts[0]), int(parts[1])
        if m < 1 or m > 12:
            return None
        from_m = date(y, m, 1)
        if m == 12:
            to_m = from_m.replace(year=y + 1, month=1) - timedelta(days=1)
        else:
            to_m = from_m.replace(month=m + 1) - timedelta(days=1)
        return (from_m, to_m)
    except (ValueError, TypeError):
        return None


@router.get("/admin/dashboard-metrics", response_model=DashboardMetricsResponse)
async def admin_dashboard_metrics(
    funnel_month: Optional[str] = Query(None, description="Воронка за месяц: YYYY-MM или пусто для «Общее»"),
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Метрики для блока над таблицей пользователей: воронка, файлы, всего, таблица по месяцам."""
    schema = settings.DB_SCHEMA
    today = date.today()
    d30 = today - timedelta(days=30)
    funnel_range = _parse_funnel_month(funnel_month)

    funnel_visited = 0
    funnel_tried = 0
    funnel_registered = 0
    funnel_paid = 0
    try:
        if funnel_range is None:
            # Общее: без фильтра по дате
            r = db.execute(text(f"SELECT COUNT(*) FROM {qname('users')}")).fetchone()
            funnel_registered = r[0] or 0 if r else 0

            r = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :s AND table_name = 'landing_visits'
            """), {"s": schema}).fetchone()
            if r:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT visitor_key) FROM {qname('landing_visits')}
                """)).fetchone()
                funnel_visited = r2[0] or 0 if r2 else 0

            r = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :s AND table_name = 'promo_try_clicks'
            """), {"s": schema}).fetchone()
            if r:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT visitor_key) FROM {qname('promo_try_clicks')}
                """)).fetchone()
                funnel_tried = r2[0] or 0 if r2 else 0

            r2 = db.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :s AND table_name = 'users' AND column_name = 'paid_amount'
            """), {"s": schema}).fetchone()
            if r2:
                r3 = db.execute(text(f"""
                    SELECT COUNT(*) FROM {qname('users')}
                    WHERE COALESCE(paid_amount, 0) > 0
                """)).fetchone()
                funnel_paid = r3[0] or 0 if r3 else 0
            else:
                r3 = db.execute(text(f"""
                    SELECT COUNT(*) FROM {qname('users')}
                    WHERE COALESCE(LOWER(TRIM(plan)), 'trial') = 'paid'
                """)).fetchone()
                funnel_paid = r3[0] or 0 if r3 else 0
        else:
            from_m, to_m = funnel_range
            # За месяц: фильтр по датам
            r = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('users')}
                WHERE created_at::date >= :from_d AND created_at::date <= :to_d
            """), {"from_d": from_m, "to_d": to_m}).fetchone()
            funnel_registered = r[0] or 0 if r else 0

            r = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :s AND table_name = 'landing_visits'
            """), {"s": schema}).fetchone()
            if r:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT visitor_key) FROM {qname('landing_visits')}
                    WHERE created_at::date >= :from_d AND created_at::date <= :to_d
                """), {"from_d": from_m, "to_d": to_m}).fetchone()
                funnel_visited = r2[0] or 0 if r2 else 0

            r = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :s AND table_name = 'promo_try_clicks'
            """), {"s": schema}).fetchone()
            if r:
                r2 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT visitor_key) FROM {qname('promo_try_clicks')}
                    WHERE created_at::date >= :from_d AND created_at::date <= :to_d
                """), {"from_d": from_m, "to_d": to_m}).fetchone()
                funnel_tried = r2[0] or 0 if r2 else 0

            try:
                r3 = db.execute(text(f"""
                    SELECT COUNT(DISTINCT user_id) FROM {qname('user_payments')}
                    WHERE paid_at::date >= :from_d AND paid_at::date <= :to_d
                """), {"from_d": from_m, "to_d": to_m}).fetchone()
                funnel_paid = r3[0] or 0 if r3 else 0
            except Exception:
                funnel_paid = 0
    except Exception as e:
        logger.warning("Admin dashboard_metrics funnel: %s", e)
        db.rollback()

    conversion_pct = (funnel_paid / funnel_registered * 100) if funnel_registered else 0.0
    funnel = DashboardFunnel(
        visited_site=funnel_visited,
        tried=funnel_tried,
        registered=funnel_registered,
        paid=funnel_paid,
        conversion_pct=round(conversion_pct, 1),
    )

    files_total = 0
    files_errors = 0
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :s AND table_name = 'import_file_attempts'
        """), {"s": schema}).fetchone()
        if r:
            row = db.execute(text(f"""
                SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'failed')
                FROM {qname('import_file_attempts')}
            """)).fetchone()
            if row:
                files_total = row[0] or 0
                files_errors = row[1] or 0
        else:
            row = db.execute(text(f"SELECT COUNT(*) FROM {qname('upload_batch')}")).fetchone()
            files_total = row[0] or 0 if row else 0
            # Ошибки = батчи без данных в fact-таблицах (упрощённо не считаем по батчам — 0)
            files_errors = 0
    except Exception as e:
        logger.warning("Admin dashboard_metrics files: %s", e)
        db.rollback()
    error_pct = (files_errors / files_total * 100) if files_total else 0.0
    files = DashboardFiles(total=files_total, errors=files_errors, error_pct=round(error_pct, 1))

    totals_paid = funnel_paid
    inactive_30d = 0
    try:
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name = 'last_login_at'
        """), {"s": schema}).fetchone()
        if r:
            # Неактивны более 30 дней: не заходили 30+ дней (дата входа — last_login_at в таблице users)
            r2 = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('users')}
                WHERE last_login_at IS NULL OR last_login_at::date <= :d30
            """), {"d30": d30}).fetchone()
            inactive_30d = r2[0] or 0 if r2 else 0
        else:
            inactive_30d = funnel_registered
    except Exception as e:
        logger.warning("Admin dashboard_metrics totals: %s", e)
        db.rollback()
    totals = DashboardTotals(
        registered=funnel_registered,
        paid_subscription=totals_paid,
        inactive_30d=inactive_30d,
    )

    monthly: list[MonthlyRow] = []
    try:
        db.rollback()
        end_date = today
        for i in range(12):  # i=0 — текущий месяц, i=1 — предыдущий, …
            m = end_date.month - i
            y = end_date.year
            while m < 1:
                m += 12
                y -= 1
            from_m = date(y, m, 1)
            if m == 12:
                to_m = from_m.replace(year=from_m.year + 1, month=1) - timedelta(days=1)
            else:
                to_m = from_m.replace(month=from_m.month + 1) - timedelta(days=1)
            if to_m > end_date:
                to_m = end_date
            month_key = from_m.strftime("%Y-%m")
            month_label = f"{_MONTH_LABELS[from_m.month - 1]} {from_m.year}"

            reg_count = 0
            rev = 0.0
            pay_count = 0
            active_users = 0
            # Дата регистрации в UTC, чтобы февраль и другие месяцы считались одинаково независимо от TZ сервера
            r = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('users')}
                WHERE (created_at AT TIME ZONE 'UTC')::date >= :from_d AND (created_at AT TIME ZONE 'UTC')::date <= :to_d
            """), {"from_d": from_m, "to_d": to_m}).fetchone()
            if r:
                reg_count = r[0] or 0
            try:
                r2 = db.execute(text(f"""
                    SELECT COALESCE(SUM(amount), 0), COUNT(*)
                    FROM {qname('user_payments')}
                    WHERE paid_at::date >= :from_d AND paid_at::date <= :to_d
                """), {"from_d": from_m, "to_d": to_m}).fetchone()
                if r2:
                    rev = float(r2[0] or 0)
                    pay_count = int(r2[1] or 0)
            except Exception:
                pass
            # Подписчики за месяц = кол-во аккаунтов с тарифом Month 5 или Month 10, оплативших в этом месяце
            try:
                r_plan = db.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = :s AND table_name = 'users' AND column_name = 'plan'
                """), {"s": schema}).fetchone()
                if r_plan:
                    r4 = db.execute(text(f"""
                        SELECT COUNT(DISTINCT up.user_id)
                        FROM {qname('user_payments')} up
                        INNER JOIN {qname('users')} u ON u.id = up.user_id
                        WHERE up.paid_at::date >= :from_d AND up.paid_at::date <= :to_d
                          AND LOWER(TRIM(COALESCE(u.plan, ''))) IN ('month 5', 'month 10', 'month_5', 'month_10', 'month5', 'month10')
                    """), {"from_d": from_m, "to_d": to_m}).fetchone()
                    active_users = r4[0] or 0 if r4 else 0
            except Exception:
                pass
            monthly.append(MonthlyRow(
                month=month_key,
                month_label=month_label,
                profit=round(rev, 0),
                registrations=reg_count,
                payments=pay_count,
                active_users=active_users,
            ))
    except Exception as e:
        logger.warning("Admin dashboard_metrics monthly: %s", e)
        db.rollback()

    return DashboardMetricsResponse(funnel=funnel, files=files, totals=totals, monthly=monthly)


@router.get("/admin/tenants", response_model=TenantsListResponse)
async def admin_tenants_list(
    search: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    import_status: Optional[str] = Query(None),
    freshness_bucket: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    has_failures_7d: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at"),
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List tenants (users) with filters and pagination."""
    schema = settings.DB_SCHEMA
    today = date.today()
    has_created_at = False
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'upload_batch' AND column_name = 'created_at'
        """), {"s": schema}).fetchone()
        has_created_at = r is not None
    except Exception:
        pass

    has_import_file_attempts = False
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :s AND table_name = 'import_file_attempts'
        """), {"s": schema}).fetchone()
        has_import_file_attempts = r is not None
    except Exception:
        pass

    # Build tenant list from users + last batch + data freshness
    # Simple query: all users, then enrich with subqueries
    order_col = "created_at"
    if sort in ("created_at", "last_import_at", "data_freshness", "imports_30d"):
        order_col = sort

    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}
    search_cond = ""
    if search and search.strip():
        search_cond = " AND (u.email ILIKE :search OR u.full_name ILIKE :search OR u.id::text = :search_exact)"
        params["search"] = f"%{search.strip()}%"
        params["search_exact"] = search.strip()

    # Check plan column exists before filtering by plan
    has_plan_cols = False
    has_paid_amount = False
    try:
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name IN ('plan','trial_ends_at','admin_notes','paid_amount')
        """), {"s": schema}).fetchall()
        col_set = {row[0] for row in (r or [])}
        has_plan_cols = len(col_set & {"plan", "trial_ends_at", "admin_notes"}) >= 3
        has_paid_amount = "paid_amount" in col_set
    except Exception:
        pass

    plan_cond = ""
    if plan and plan.strip() and has_plan_cols:
        plan_cond = " AND COALESCE(u.plan, 'trial') = :plan"
        params["plan"] = plan.strip()

    # Count total
    count_sql = f"""
        SELECT COUNT(*) FROM {qname('users')} u
        WHERE 1=1 {search_cond} {plan_cond}
    """
    total = db.execute(text(count_sql), params).scalar() or 0

    # Get users with optional columns (plan, trial_ends_at, admin_notes, last_login_at, phone)
    cols = "id, email, full_name, created_at, is_active"
    try:
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name IN ('phone', 'last_login_at')
        """), {"s": schema}).fetchall()
        col_names = [row[0] for row in (r or [])]
        has_phone = "phone" in col_names
        has_last_login = "last_login_at" in col_names
    except Exception:
        has_phone = has_last_login = False
    if has_phone:
        cols += ", phone"
    else:
        cols += ", NULL::varchar AS phone"
    if has_last_login:
        cols += ", last_login_at"
    else:
        cols += ", NULL::timestamptz AS last_login_at"
    if has_plan_cols:
        cols += ", COALESCE(plan,'trial') AS plan, trial_ends_at, admin_notes"
    else:
        cols += ", 'trial' AS plan, NULL::timestamptz AS trial_ends_at, NULL::text AS admin_notes"
    if has_paid_amount:
        cols += ", paid_amount"
    else:
        cols += ", NULL::numeric AS paid_amount"

    list_sql = f"""
        SELECT {cols} FROM {qname('users')} u
        WHERE 1=1 {search_cond} {plan_cond}
        ORDER BY u.created_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(list_sql), params).fetchall()
    tenants_out: list[TenantRow] = []

    for row in rows or []:
        uid = str(row[0])
        email = row[1]
        full_name = row[2]
        created_at = _safe_ts(row, 3)
        is_active = row[4] if len(row) > 4 else True
        phone = row[5] if len(row) > 5 and row[5] else None
        last_login_at_val = _safe_ts(row, 6) if len(row) > 6 else None
        plan_val = row[7] if len(row) > 7 else "trial"
        trial_ends_at = _safe_ts(row, 8) if len(row) > 8 else None
        notes = row[9] if len(row) > 9 else None
        paid_amount_val = float(row[10]) if len(row) > 10 and row[10] is not None else None

        last_import_at = None
        last_import_status = None
        last_import_type = None
        imports_30d = 0
        failed_30d = 0
        data_freshness_days = None
        shops_count = 0

        if has_created_at:
            b = db.execute(text(f"""
                SELECT upload_batch_id, created_at, status
                FROM {qname('upload_batch')}
                WHERE user_id = :uid
                ORDER BY created_at DESC NULLS LAST
                LIMIT 1
            """), {"uid": uid}).fetchone()
            if b:
                last_import_at = _safe_ts(b, 1)
                last_import_status = (b[2] or "processing").lower()
                last_import_type = "xlsx"
                # Успех = загрузка Excel прошла успешно = есть ≥1 строка в любой fact-таблице
                has_any = db.execute(text(f"""
                    SELECT 1 FROM {qname('fact_sales')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                """), {"uid": uid, "bid": str(b[0])}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_expenses')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": str(b[0])}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_leftout_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": str(b[0])}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_storage_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": str(b[0])}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_leftout_old_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": str(b[0])}).fetchone()
                last_import_status = "success" if has_any else "failed"

            # Импорты 30д = только количество загрузок (upload_batch) за 30 дней
            r30_count = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('upload_batch')} b
                WHERE b.user_id = :uid AND b.created_at >= :d30
            """), {"uid": uid, "d30": today - timedelta(days=30)}).fetchone()
            if r30_count:
                imports_30d = r30_count[0] or 0
            if has_import_file_attempts:
                r30_failed = db.execute(text(f"""
                    SELECT COUNT(*) FILTER (WHERE a.status = 'failed')
                    FROM {qname('import_file_attempts')} a
                    JOIN {qname('upload_batch')} b ON b.upload_batch_id = a.upload_batch_id
                    WHERE b.user_id = :uid AND a.created_at >= :d30
                """), {"uid": uid, "d30": today - timedelta(days=30)}).fetchone()
                if r30_failed:
                    failed_30d = r30_failed[0] or 0
            else:
                r30_failed = db.execute(text(f"""
                    SELECT COUNT(*) FROM {qname('upload_batch')} b
                    WHERE b.user_id = :uid AND b.created_at >= :d30
                      AND NOT (
                             EXISTS (SELECT 1 FROM {qname('fact_sales')} fs WHERE fs.user_id = b.user_id AND fs.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_expenses')} fe WHERE fe.user_id = b.user_id AND fe.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_leftout_snapshot')} fl WHERE fl.user_id = b.user_id AND fl.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_storage_snapshot')} fss WHERE fss.user_id = b.user_id AND fss.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_leftout_old_snapshot')} flo WHERE flo.user_id = b.user_id AND flo.upload_batch_id = b.upload_batch_id)
                           )
                """), {"uid": uid, "d30": today - timedelta(days=30)}).fetchone()
                if r30_failed:
                    failed_30d = r30_failed[0] or 0

            # Data freshness: max date_created from fact_sales for this user
            df = db.execute(text(f"""
                SELECT (CURRENT_DATE - MAX(date_created)::date) FROM {qname('fact_sales')}
                WHERE user_id = :uid
            """), {"uid": uid}).fetchone()
            if df and df[0] is not None:
                data_freshness_days = int(df[0])

        # Количество магазинов (dim_shop), без «все»/заглушки (Не определено)
        try:
            sc = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('dim_shop')}
                WHERE user_id = :uid AND COALESCE(trim(shop_name), '') != '(Не определено)'
            """), {"uid": uid}).scalar()
            shops_count = sc or 0
        except Exception:
            pass

        # Остаток дней триала; оплачено = plan paid
        trial_days_left = None
        if trial_ends_at:
            try:
                if isinstance(trial_ends_at, str):
                    te = date.fromisoformat(trial_ends_at[:10])
                else:
                    te = getattr(trial_ends_at, "date", lambda: trial_ends_at)() if hasattr(trial_ends_at, "date") else trial_ends_at
                trial_days_left = (te - today).days
                # В админке не уходим в минус — минимум 0
                if trial_days_left is not None and trial_days_left < 0:
                    trial_days_left = 0
            except Exception:
                pass
        paid = (plan_val or "").lower() == "paid"
        status = "active" if is_active else "blocked"

        tenants_out.append(TenantRow(
            tenant_id=uid,
            company_name=full_name or email or None,
            owner_email=email,
            created_at=created_at[:10] if created_at else None,
            plan=plan_val,
            trial_ends_at=trial_ends_at[:10] if trial_ends_at else None,
            next_billing_date=None,
            payment_status=None,
            last_activity_at=last_import_at,
            last_import_at=last_import_at,
            last_import_status=last_import_status,
            last_import_type=last_import_type,
            data_freshness_days=data_freshness_days,
            imports_30d=imports_30d,
            failed_imports_30d=failed_30d,
            storage_mb=None,
            top_last_error=None,
            notes=notes,
            is_active=bool(is_active),
            phone=phone,
            shops_count=shops_count,
            status=status,
            trial_days_left=trial_days_left,
            paid=paid,
            paid_amount=paid_amount_val,
            last_login_at=last_login_at_val[:10] if last_login_at_val else None,
        ))

    return TenantsListResponse(tenants=tenants_out, total_count=total)


@router.get("/admin/tenants/{tenant_id}/shops", response_model=TenantShopsResponse)
async def admin_tenant_shops(
    tenant_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Список магазинов по тенанту (для подсказки в админке).

    Источник: dim_shop, те же магазины, что учитываются в shops_count:
    - user_id = tenant_id
    - shop_name не пустой и не '(Не определено)'.
    """
    uid = str(tenant_id)
    shops: list[str] = []
    try:
        rows = db.execute(
            text(
                f"""
                SELECT DISTINCT shop_name
                FROM {qname('dim_shop')}
                WHERE user_id = :uid
                  AND shop_name IS NOT NULL
                  AND TRIM(shop_name) <> ''
                  AND COALESCE(trim(shop_name), '') != '(Не определено)'
                ORDER BY shop_name
                """
            ),
            {"uid": uid},
        ).fetchall()
        shops = [str(r[0]) for r in rows or []]
    except Exception as e:
        logger.debug("admin_tenant_shops failed for %s: %s", uid, e)

    return TenantShopsResponse(tenant_id=uid, shops=shops)


@router.get("/admin/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def admin_tenant_detail(
    tenant_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Tenant (user) detail for admin."""
    uid = str(tenant_id)
    row = db.execute(text(f"""
        SELECT id, email, full_name, created_at, is_active
        FROM {qname('users')}
        WHERE id = :uid
    """), {"uid": uid}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan_val = "trial"
    trial_ends_at_val = None
    notes_val = None
    try:
        r = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = :s AND table_name = 'users' AND column_name IN ('plan','trial_ends_at','admin_notes')
        """), {"s": settings.DB_SCHEMA}).fetchall()
        if r and len(r) >= 3:
            ext = db.execute(text(f"""
                SELECT COALESCE(plan,'trial'), trial_ends_at, admin_notes FROM {qname('users')} WHERE id = :uid
            """), {"uid": uid}).fetchone()
            if ext:
                plan_val = ext[0] or "trial"
                trial_ends_at_val = ext[1]
                notes_val = ext[2]
    except Exception:
        pass

    last_import_at = None
    last_batch_id = None
    last_status = None
    imports_30d = 0
    failed_30d = 0
    data_freshness_days = None
    has_import_file_attempts_detail = False
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = 'import_file_attempts'
        """), {"schema": settings.DB_SCHEMA}).fetchone()
        has_import_file_attempts_detail = r is not None
    except Exception:
        pass
    try:
        r = db.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'upload_batch' AND column_name = 'created_at'
        """), {"schema": settings.DB_SCHEMA}).fetchone()
        if r:
            b = db.execute(text(f"""
                SELECT upload_batch_id, created_at, status
                FROM {qname('upload_batch')} WHERE user_id = :uid
                ORDER BY created_at DESC NULLS LAST LIMIT 1
            """), {"uid": uid}).fetchone()
            if b:
                last_batch_id = str(b[0])
                last_import_at = _safe_ts(b, 1)
                has_any = db.execute(text(f"""
                    SELECT 1 FROM {qname('fact_sales')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                """), {"uid": uid, "bid": last_batch_id}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_expenses')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": last_batch_id}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_leftout_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": last_batch_id}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_storage_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": last_batch_id}).fetchone()
                if not has_any:
                    has_any = db.execute(text(f"""
                        SELECT 1 FROM {qname('fact_leftout_old_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1
                    """), {"uid": uid, "bid": last_batch_id}).fetchone()
                last_status = "success" if has_any else "failed"
            # Импорты 30д = только количество загрузок (upload_batch) за 30 дней
            r30_count = db.execute(text(f"""
                SELECT COUNT(*) FROM {qname('upload_batch')} b
                WHERE b.user_id = :uid AND b.created_at >= :d30
            """), {"uid": uid, "d30": date.today() - timedelta(days=30)}).fetchone()
            if r30_count:
                imports_30d = r30_count[0] or 0
            if has_import_file_attempts_detail:
                r30_failed = db.execute(text(f"""
                    SELECT COUNT(*) FILTER (WHERE a.status = 'failed')
                    FROM {qname('import_file_attempts')} a
                    JOIN {qname('upload_batch')} b ON b.upload_batch_id = a.upload_batch_id
                    WHERE b.user_id = :uid AND a.created_at >= :d30
                """), {"uid": uid, "d30": date.today() - timedelta(days=30)}).fetchone()
                if r30_failed:
                    failed_30d = r30_failed[0] or 0
            else:
                r30_failed = db.execute(text(f"""
                    SELECT COUNT(*) FROM {qname('upload_batch')} b
                    WHERE b.user_id = :uid AND b.created_at >= :d30
                      AND NOT (
                             EXISTS (SELECT 1 FROM {qname('fact_sales')} fs WHERE fs.user_id = b.user_id AND fs.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_expenses')} fe WHERE fe.user_id = b.user_id AND fe.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_leftout_snapshot')} fl WHERE fl.user_id = b.user_id AND fl.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_storage_snapshot')} fss WHERE fss.user_id = b.user_id AND fss.upload_batch_id = b.upload_batch_id)
                             OR EXISTS (SELECT 1 FROM {qname('fact_leftout_old_snapshot')} flo WHERE flo.user_id = b.user_id AND flo.upload_batch_id = b.upload_batch_id)
                           )
                """), {"uid": uid, "d30": date.today() - timedelta(days=30)}).fetchone()
                if r30_failed:
                    failed_30d = r30_failed[0] or 0
            df = db.execute(text(f"""
                SELECT (CURRENT_DATE - MAX(date_created)::date) FROM {qname('fact_sales')} WHERE user_id = :uid
            """), {"uid": uid}).fetchone()
            if df and df[0] is not None:
                data_freshness_days = int(df[0])
    except Exception as e:
        logger.warning(f"Admin tenant detail enrichment: {e}")
        db.rollback()

    return TenantDetailResponse(
        tenant_id=uid,
        company_name=row[2] or row[1],
        owner_email=row[1],
        created_at=_safe_ts(row, 3),
        plan=plan_val,
        trial_ends_at=trial_ends_at_val.isoformat() if trial_ends_at_val and hasattr(trial_ends_at_val, "isoformat") else (str(trial_ends_at_val) if trial_ends_at_val else None),
        notes=notes_val,
        is_active=bool(row[4]),
        last_import_at=last_import_at,
        last_import_batch_id=last_batch_id,
        last_import_status=last_status,
        data_freshness_days=data_freshness_days,
        imports_30d=imports_30d,
        failed_imports_30d=failed_30d,
    )


@router.get("/admin/imports/{import_id}/log")
async def admin_import_log(
    import_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return last import (batch) info for admin. No secrets (no DSN, passwords)."""
    bid = str(import_id)
    row = db.execute(text(f"""
        SELECT b.upload_batch_id, b.user_id, b.status, b.created_at, b.updated_at
        FROM {qname('upload_batch')} b
        WHERE b.upload_batch_id = :bid
    """), {"bid": bid}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Import not found")
    uid = str(row[1])
    has_fs = db.execute(text(f"SELECT 1 FROM {qname('fact_sales')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1"), {"uid": uid, "bid": bid}).fetchone()
    has_fe = db.execute(text(f"SELECT 1 FROM {qname('fact_expenses')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1"), {"uid": uid, "bid": bid}).fetchone()
    has_fl = db.execute(text(f"SELECT 1 FROM {qname('fact_leftout_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1"), {"uid": uid, "bid": bid}).fetchone()
    has_fss = db.execute(text(f"SELECT 1 FROM {qname('fact_storage_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1"), {"uid": uid, "bid": bid}).fetchone()
    has_flo = db.execute(text(f"SELECT 1 FROM {qname('fact_leftout_old_snapshot')} WHERE user_id = :uid AND upload_batch_id = :bid LIMIT 1"), {"uid": uid, "bid": bid}).fetchone()
    has_any_data = bool(has_fs or has_fe or has_fl or has_fss or has_flo)
    return {
        "import_id": bid,
        "user_id": uid,
        "status": row[2],
        "created_at": _safe_ts(row, 3),
        "updated_at": _safe_ts(row, 4),
        "has_sales_data": bool(has_fs),
        "has_any_data": has_any_data,
        "message": "No log storage; batch metadata only.",
    }


@router.post("/admin/imports/{import_id}/retry")
async def admin_import_retry(
    import_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retry import. No queue in MVP - returns 501."""
    raise HTTPException(status_code=501, detail="Retry not implemented (no job queue)")


class ExtendTrialBody(BaseModel):
    days: int = 7


@router.post("/admin/tenants/{tenant_id}/disable")
async def admin_tenant_disable(
    tenant_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Disable tenant (set is_active = false)."""
    uid = str(tenant_id)
    try:
        db.execute(text(f"UPDATE {qname('users')} SET is_active = false, updated_at = now() WHERE id = :uid"), {"uid": uid})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": uid, "is_active": False}


@router.post("/admin/tenants/{tenant_id}/enable")
async def admin_tenant_enable(
    tenant_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enable tenant (set is_active = true)."""
    uid = str(tenant_id)
    try:
        db.execute(text(f"UPDATE {qname('users')} SET is_active = true, updated_at = now() WHERE id = :uid"), {"uid": uid})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": uid, "is_active": True}


@router.post("/admin/tenants/{tenant_id}/extend-trial")
async def admin_tenant_extend_trial(
    tenant_id: UUID,
    body: ExtendTrialBody,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Extend trial_ends_at by body.days (from now or current trial_ends_at)."""
    uid = str(tenant_id)
    try:
        # Get current trial_ends_at
        r = db.execute(text(f"SELECT trial_ends_at FROM {qname('users')} WHERE id = :uid"), {"uid": uid}).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Tenant not found")
        base = r[0] or datetime.now(timezone.utc)
        if base < datetime.now(timezone.utc):
            base = datetime.now(timezone.utc)
        new_end = base + timedelta(days=body.days)
        db.execute(text(f"""
            UPDATE {qname('users')} SET trial_ends_at = :end, updated_at = now() WHERE id = :uid
        """), {"uid": uid, "end": new_end})
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": uid, "trial_ends_at": new_end.isoformat()}


class PaymentBody(BaseModel):
    amount: float  # сумма оплаты (попадает в колонку Оплачено и в график дохода по месяцу paid_at)
    paid_at: Optional[str] = None  # ISO datetime; по умолчанию now()
    plan: Optional[str] = None  # тариф, на который переключается пользователь при оплате: "month_5" или "month_10"


@router.post("/admin/tenants/{tenant_id}/payment")
async def admin_tenant_payment(
    tenant_id: UUID,
    body: PaymentBody,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Записать платёж клиента: сумма в «Оплачено» и график. Если указан plan (month_5/month_10), пользователь переключается на этот тариф и получает 30 дней доступа."""
    uid = str(tenant_id)
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    try:
        r = db.execute(text(f"SELECT id FROM {qname('users')} WHERE id = :uid"), {"uid": uid}).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Tenant not found")
        paid_at = datetime.now(timezone.utc)
        if body.paid_at:
            try:
                paid_at = datetime.fromisoformat(body.paid_at.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="paid_at must be ISO datetime")
        # Убедиться, что таблица и колонки существуют (если миграции не применялись к этой БД)
        schema = get_settings().DB_SCHEMA
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.user_payments (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                amount numeric(18,2) NOT NULL,
                paid_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_user_payments_user_id ON {schema}.user_payments (user_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_user_payments_paid_at ON {schema}.user_payments (paid_at)"))
        db.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS paid_amount numeric(18,2) NOT NULL DEFAULT 0"))
        db.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz"))
        db.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS plan varchar(50) NOT NULL DEFAULT 'trial'"))
        db.execute(text(f"""
            INSERT INTO {qname('user_payments')} (user_id, amount, paid_at)
            VALUES (:uid, :amount, :paid_at)
        """), {"uid": uid, "amount": body.amount, "paid_at": paid_at})
        db.execute(text(f"""
            UPDATE {qname('users')} SET paid_amount = COALESCE(paid_amount, 0) + :amount, updated_at = now() WHERE id = :uid
        """), {"uid": uid, "amount": body.amount})
        # Если указан тариф при оплате — переключаем на тариф и даём 30 дней. Смена тарифа = обнуление дней; докупка того же = прибавка 30 дней.
        plan_canonical = None
        if body.plan and body.plan.strip():
            plan_key = body.plan.strip().lower().replace(" ", "_")
            if plan_key in ("month_5", "month5"):
                plan_canonical = "Month 5"
            elif plan_key in ("month_10", "month10"):
                plan_canonical = "Month 10"
        # Текущий план пользователя для решения: смена тарифа (обнулить дни) или докупка (прибавить 30 дней)
        plan_row = db.execute(text(f"""
            SELECT LOWER(TRIM(COALESCE(plan, ''))) FROM {qname('users')} WHERE id = :uid
        """), {"uid": uid}).fetchone()
        current_plan_norm = (plan_row[0] or "").strip().replace(" ", "_") if plan_row else ""
        if plan_canonical:
            is_same_plan = (
                (plan_canonical == "Month 5" and current_plan_norm in ("month_5", "month5"))
                or (plan_canonical == "Month 10" and current_plan_norm in ("month_10", "month10"))
            )
            if is_same_plan:
                # Докупка того же тарифа — прибавляем 30 дней
                db.execute(text(f"""
                    UPDATE {qname('users')}
                    SET plan = :plan,
                        trial_ends_at = GREATEST(COALESCE(trial_ends_at, :paid_at), :paid_at) + INTERVAL '30 days',
                        updated_at = now()
                    WHERE id = :uid
                """), {"uid": uid, "plan": plan_canonical, "paid_at": paid_at})
            else:
                # Смена тарифа — обнуляем остаток, ставим 30 дней от даты оплаты
                db.execute(text(f"""
                    UPDATE {qname('users')}
                    SET plan = :plan,
                        trial_ends_at = :paid_at + INTERVAL '30 days',
                        updated_at = now()
                    WHERE id = :uid
                """), {"uid": uid, "plan": plan_canonical, "paid_at": paid_at})
        else:
            # Без указания тарифа: продлеваем на 30 дней только если уже Month 5 / Month 10
            if current_plan_norm in ("month_5", "month_10", "month5", "month10"):
                db.execute(text(f"""
                    UPDATE {qname('users')}
                    SET trial_ends_at = GREATEST(COALESCE(trial_ends_at, :paid_at), :paid_at) + INTERVAL '30 days',
                        updated_at = now()
                    WHERE id = :uid
                """), {"uid": uid, "paid_at": paid_at})
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    out = {"ok": True, "tenant_id": uid, "amount": body.amount, "paid_at": paid_at.isoformat()}
    if plan_canonical:
        out["plan"] = plan_canonical
    return out


class NotesBody(BaseModel):
    notes: Optional[str] = None


@router.patch("/admin/tenants/{tenant_id}/notes")
async def admin_tenant_notes(
    tenant_id: UUID,
    body: NotesBody,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update internal admin notes for tenant."""
    uid = str(tenant_id)
    try:
        db.execute(text(f"""
            UPDATE {qname('users')} SET admin_notes = :notes, updated_at = now() WHERE id = :uid
        """), {"uid": uid, "notes": body.notes or ""})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": uid, "notes": body.notes}


class SetPasswordBody(BaseModel):
    password: str


@router.post("/admin/tenants/{tenant_id}/set-password")
async def admin_tenant_set_password(
    tenant_id: UUID,
    body: SetPasswordBody,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Переписать только пароль у существующей записи входа по email.
    Обновляется только колонка password_hash (provider и identifier не трогаем — избегаем ошибок enum).
    """
    password = (body.password or "").strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Пароль не менее 6 символов")
    user = db.query(User).filter(User.id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    email = (user.email or "").strip()
    if not email:
        raise HTTPException(
            status_code=400,
            detail="У пользователя не указан email. Укажите email в карточке клиента, затем установите пароль.",
        )
    try:
        password_hash = hash_password(password)
        # Только UPDATE password_hash по user_id и email (без учёта регистра) — не трогаем provider (enum в БД)
        r = db.execute(
            text(f"""
                UPDATE {qname('auth_identities')}
                SET password_hash = :pw
                WHERE user_id = CAST(:uid AS uuid) AND LOWER(identifier) = LOWER(:email) AND password_hash IS NOT NULL
                RETURNING id
            """),
            {"uid": str(tenant_id), "pw": password_hash, "email": email},
        ).fetchone()
        if not r:
            raise HTTPException(
                status_code=404,
                detail="У клиента нет входа по email/паролю. Сначала зайдите под этим пользователем или зарегистрируйте его.",
            )
        # Отозвать все refresh-токены
        db.query(RefreshToken).filter(RefreshToken.user_id == tenant_id).update(
            {RefreshToken.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False
        )
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("set-password failed for tenant_id=%s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": str(tenant_id), "message": "Пароль изменён. Вход только с новым паролем."}


def _table_missing(exc: Exception) -> bool:
    """Пропускать только ошибку «таблица/relation не существует»."""
    msg = (getattr(exc, "message", "") or str(exc)).lower()
    return "does not exist" in msg or "undefined_table" in msg or "relation" in msg and "exist" in msg


@router.delete("/admin/tenants/{tenant_id}")
async def admin_tenant_delete(
    tenant_id: UUID,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Удалить аккаунт клиента и все загруженные данные (безвозвратно)."""
    uid = str(tenant_id)
    # Порядок: факты/стаджинги по user_id, map_*, manual_expenses, dim_shop, upload_batch, auth, users
    tables_user = [
        "fact_sales", "fact_expenses", "fact_storage_snapshot", "fact_leftout_snapshot",
        "fact_leftout_old_snapshot",
        "stg_sales", "stg_expenses", "stg_storage", "stg_leftout", "stg_leftout_old",
        "map_shop_sku", "map_shop_barcode",
        "manual_expenses", "dim_shop", "upload_batch",
    ]
    try:
        for tbl in tables_user:
            try:
                db.execute(text(f"DELETE FROM {qname(tbl)} WHERE user_id = :uid"), {"uid": uid})
            except Exception as e:
                if _table_missing(e):
                    pass
                else:
                    raise
        for tbl in ["refresh_tokens", "auth_identities", "verification_codes"]:
            try:
                db.execute(text(f"DELETE FROM {qname(tbl)} WHERE user_id = :uid"), {"uid": uid})
            except Exception as e:
                if _table_missing(e):
                    pass
                else:
                    raise
        db.execute(text(f"DELETE FROM {qname('users')} WHERE id = :uid"), {"uid": uid})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("admin_tenant_delete failed for %s", uid)
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "tenant_id": uid, "message": "Аккаунт и данные удалены"}
