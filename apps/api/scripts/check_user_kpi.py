"""Check KPI-style metrics for a user (30d, all shops)."""
import sys

from sqlalchemy import text

from app.db import SessionLocal, qname
from app.routes.kpi import get_data_end_date, period_range
from app.settings import get_settings
from app.utils.metrics import get_status_conditions, sql_cogs_line_amount, sql_stock_cogs_line_amount


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "mr.romanx@mail.ru"
    settings = get_settings()
    db = SessionLocal()
    db.execute(text(f"SET search_path TO {settings.DB_SCHEMA}, public"))

    user = db.execute(
        text(f"SELECT id, email FROM {qname('users')} WHERE lower(email) = lower(:e) LIMIT 1"),
        {"e": email},
    ).fetchone()
    if not user:
        print(f"USER_NOT_FOUND: {email}")
        db.close()
        return

    uid_s = str(user[0])
    data_end = get_data_end_date(db, user[0])
    pr = period_range("30d", data_end)
    rev = get_status_conditions()["revenue"]
    params = {"uid": uid_s, "df": pr["date_from"], "dt": pr["date_to"]}

    print(f"email: {user[1]}")
    print(f"user_id: {uid_s}")
    print(f"period_30d: {pr['date_from']} .. {pr['date_to']} (data_end={data_end})")

    revenue = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(CASE WHEN ({rev}) THEN revenue_sum ELSE 0 END), 0)
            FROM {qname('fact_sales')}
            WHERE user_id = CAST(:uid AS uuid)
              AND date_created >= CAST(:df AS date)
              AND date_created < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    commission = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(CASE WHEN ({rev}) THEN commission_sum ELSE 0 END), 0)
            FROM {qname('fact_sales')}
            WHERE user_id = CAST(:uid AS uuid)
              AND date_created >= CAST(:df AS date)
              AND date_created < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    logistics = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(CASE WHEN ({rev}) THEN logistics_sum ELSE 0 END), 0)
            FROM {qname('fact_sales')}
            WHERE user_id = CAST(:uid AS uuid)
              AND date_created >= CAST(:df AS date)
              AND date_created < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    product_cost = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(CASE WHEN ({rev}) THEN ({sql_cogs_line_amount('fact_sales')}) ELSE 0 END), 0)
            FROM {qname('fact_sales')} fact_sales
            WHERE fact_sales.user_id = CAST(:uid AS uuid)
              AND fact_sales.date_created >= CAST(:df AS date)
              AND fact_sales.date_created < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    exp = db.execute(
        text(
            f"""
            SELECT
              COALESCE(SUM(CASE
                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                ELSE 0 END), 0),
              COALESCE(SUM(CASE
                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                ELSE 0 END), 0),
              COALESCE(SUM(CASE
                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.amount_sum, 0)
                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%'
                 AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.amount_sum, 0)
                ELSE 0 END), 0)
            FROM {qname('fact_expenses')} fe
            WHERE fe.user_id = CAST(:uid AS uuid)
              AND fe.date_written_off >= CAST(:df AS date)
              AND fe.date_written_off < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).fetchone()

    manual = db.execute(
        text(f"SELECT COUNT(*) FROM {qname('manual_product_cogs')} WHERE user_id = CAST(:uid AS uuid)"),
        {"uid": uid_s},
    ).scalar()
    history = db.execute(
        text(f"SELECT COUNT(*) FROM {qname('manual_product_cogs_history')} WHERE user_id = CAST(:uid AS uuid)"),
        {"uid": uid_s},
    ).scalar()

    sales_rows = db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM {qname('fact_sales')}
            WHERE user_id = CAST(:uid AS uuid)
              AND date_created >= CAST(:df AS date)
              AND date_created < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    exp_rows = db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM {qname('fact_expenses')}
            WHERE user_id = CAST(:uid AS uuid)
              AND date_written_off >= CAST(:df AS date)
              AND date_written_off < CAST(:dt AS date) + interval '1 day'
            """
        ),
        params,
    ).scalar()

    storage_rows = db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM {qname('fact_expenses')} fe
            WHERE fe.user_id = CAST(:uid AS uuid)
              AND fe.date_written_off >= CAST(:df AS date)
              AND fe.date_written_off < CAST(:dt AS date) + interval '1 day'
              AND upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД'
            """
        ),
        params,
    ).scalar()

    stock_old = qname("fact_leftout_old_snapshot")
    stock_row = db.execute(
        text(
            f"""
            WITH latest AS (
                SELECT upload_batch_id
                FROM {stock_old}
                WHERE user_id = CAST(:uid AS uuid)
                ORDER BY loaded_at DESC NULLS LAST
                LIMIT 1
            )
            SELECT
              COALESCE(SUM(COALESCE(lo.in_sale_qty, 0) * COALESCE(lo.cost_sum, 0)), 0),
              COALESCE(SUM({sql_stock_cogs_line_amount("lo")}), 0),
              COALESCE(SUM(COALESCE(lo.in_sale_qty, 0)), 0)
            FROM {stock_old} lo
            JOIN latest lb ON lb.upload_batch_id = lo.upload_batch_id
            WHERE lo.user_id = CAST(:uid AS uuid)
            """
        ),
        {"uid": uid_s},
    ).fetchone()

    rev_f = float(revenue or 0)
    pc_f = float(product_cost or 0)
    comm_f = float(commission or 0)
    log_f = float(logistics or 0)
    ads_f = float(exp[0] or 0)
    storage_f = float(exp[1] or 0)
    fines_f = float(exp[2] or 0)
    taxes = rev_f * 0.01

    print()
    print("--- KPI (30d, all shops) ---")
    print(f"revenue:           {rev_f:,.0f}")
    print(f"product_cost:      {pc_f:,.0f}")
    print(f"uzum_commission:   {comm_f:,.0f}")
    print(f"uzum_logistics:    {log_f:,.0f}")
    print(f"uzum_storage:      {storage_f:,.0f}")
    print(f"uzum_ads:          {ads_f:,.0f}")
    print(f"uzum_fines:        {fines_f:,.0f}")
    print(f"taxes_1pct:        {taxes:,.0f}")
    print(
        f"net_profit (approx): {rev_f - pc_f - comm_f - log_f - storage_f - ads_f - fines_f - taxes:,.0f}"
    )
    print()
    print(f"manual_product_cogs: {manual}, history: {history}")
    print(f"sales_rows: {sales_rows}, expense_rows: {exp_rows}, storage_rows: {storage_rows}")
    if stock_row:
        print(f"fbo_stock_qty: {float(stock_row[2] or 0):,.0f}")
        print(f"fbo_stock_cost (uzum only): {float(stock_row[0] or 0):,.0f}")
        print(f"fbo_stock_cost (effective):   {float(stock_row[1] or 0):,.0f}")

    if history:
        rows = db.execute(
            text(
                f"""
                SELECT barcode_norm, cogs_sum, effective_from
                FROM {qname('manual_product_cogs_history')}
                WHERE user_id = CAST(:uid AS uuid)
                ORDER BY effective_from DESC, created_at DESC
                LIMIT 10
                """
            ),
            {"uid": uid_s},
        ).fetchall()
        print("history sample:")
        for r in rows:
            print(f"  {r[0]} | {r[1]} | {r[2]}")

    db.close()


if __name__ == "__main__":
    main()
