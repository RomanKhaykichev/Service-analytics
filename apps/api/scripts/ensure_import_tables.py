"""
Создаёт таблицы для загрузки отчётов: sales, expenses, storage, inventory
(dim_shop, stg_*, fact_*, map_shop_sku), если их ещё нет в БД API.

Запуск из корня или из apps/api:
  cd apps/api && python scripts/ensure_import_tables.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from app.settings import get_settings


def main():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    schema = settings.DB_SCHEMA

    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()

        # dim_shop — магазины (заполняется из leftout/storage/sales)
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.dim_shop (
                shop_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL,
                shop_name text NOT NULL,
                UNIQUE (user_id, shop_name)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_dim_shop_user_id ON {schema}.dim_shop (user_id)"))
        conn.commit()

        # stg_sales — сырые данные отчёта по продажам
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stg_sales (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                row_num int NOT NULL,
                status_raw text,
                created_at_raw text,
                received_at_raw text,
                order_no_raw text,
                barcode_raw text,
                sku_raw text,
                name_raw text,
                category_raw text,
                qty_raw text,
                returns_raw text,
                revenue_raw text,
                revenue_net_raw text,
                commission_raw text,
                price_raw text,
                promo_raw text,
                cogs_raw text,
                logistics_raw text,
                barcode_norm text
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_stg_sales_user_batch ON {schema}.stg_sales (user_id, upload_batch_id)"))
        conn.commit()

        # stg_expenses — сырые данные отчёта по услугам
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stg_expenses (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                row_num int NOT NULL,
                source_raw text,
                service_raw text,
                status_raw text,
                operation_id_raw text,
                written_off_raw text,
                cost_raw text,
                qty_raw text,
                amount_raw text,
                operation_type_raw text
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_stg_expenses_user_batch ON {schema}.stg_expenses (user_id, upload_batch_id)"))
        conn.commit()

        # stg_storage — сырые данные отчёта по хранению
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stg_storage (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                row_num int NOT NULL,
                shop_raw text,
                product_name_raw text,
                product_id_raw text,
                sku_raw text,
                barcode_raw text,
                size_group_raw text,
                turnover_days_raw text,
                storage_type_raw text,
                fee_total_30d_raw text,
                barcode_norm text
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_stg_storage_user_batch ON {schema}.stg_storage (user_id, upload_batch_id)"))
        conn.commit()

        # fact_sales — агрегированные продажи (UNIQUE для ON CONFLICT в imports)
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.fact_sales (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                shop_id uuid,
                status text,
                date_created timestamptz,
                date_received timestamptz,
                order_no text,
                sku text,
                barcode text,
                product_name text,
                category text,
                barcode_norm text,
                qty int DEFAULT 0,
                returns_qty int DEFAULT 0,
                revenue_sum numeric(18,2) DEFAULT 0,
                revenue_net_sum numeric(18,2) DEFAULT 0,
                commission_sum numeric(18,2) DEFAULT 0,
                logistics_sum numeric(18,2) DEFAULT 0,
                price_sum numeric(18,2) DEFAULT 0,
                promo_sum numeric(18,2) DEFAULT 0,
                cogs_sum numeric(18,2) DEFAULT 0,
                UNIQUE (user_id, order_no, barcode, date_created)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_fact_sales_user_batch ON {schema}.fact_sales (user_id, upload_batch_id)"))
        conn.commit()

        # fact_expenses
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.fact_expenses (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                source text,
                service text,
                status text,
                operation_id text NOT NULL,
                date_written_off timestamptz,
                cost_sum numeric(18,2) DEFAULT 0,
                qty int,
                amount_sum numeric(18,2),
                operation_type text,
                UNIQUE (user_id, operation_id)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_fact_expenses_user_batch ON {schema}.fact_expenses (user_id, upload_batch_id)"))
        conn.commit()

        # fact_storage_snapshot
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.fact_storage_snapshot (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                shop_id uuid NOT NULL,
                shop_raw text,
                product_name text,
                product_id text,
                sku text NOT NULL,
                barcode text,
                barcode_norm text,
                size_group text,
                turnover_days numeric(18,4),
                storage_type text,
                fee_total_30d numeric(18,2),
                UNIQUE (user_id, upload_batch_id, shop_id, sku)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_fact_storage_snapshot_user_batch ON {schema}.fact_storage_snapshot (user_id, upload_batch_id)"))
        conn.commit()

        # map_shop_sku — привязка barcode/sku к магазину (для sales/leftout)
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.map_shop_sku (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                shop_id uuid,
                barcode text NOT NULL,
                sku text,
                UNIQUE (user_id, barcode)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_map_shop_sku_user_id ON {schema}.map_shop_sku (user_id)"))
        conn.commit()

        # stg_leftout и fact_leftout_snapshot — для отчёта "Остатки (новый)" / inventory
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stg_leftout (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                row_num int NOT NULL,
                shop_raw text,
                product_name_raw text,
                product_id_raw text,
                sku_raw text,
                barcode_raw text,
                ending_raw text,
                availability_ind_raw text,
                planned_end_raw text,
                coverage_days_raw text,
                recommended_qty_raw text,
                on_your_side_fbs_raw text,
                on_marketplace_side_raw text,
                in_supply_raw text,
                in_sale_raw text,
                to_customer_raw text,
                from_customer_raw text,
                sdh_raw text,
                photo_raw text,
                defect_raw text,
                potential_per_unit_raw text,
                potential_total_raw text,
                barcode_norm text
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_stg_leftout_user_batch ON {schema}.stg_leftout (user_id, upload_batch_id)"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.fact_leftout_snapshot (
                user_id uuid NOT NULL,
                upload_batch_id uuid NOT NULL,
                shop_id uuid NOT NULL,
                shop_raw text,
                product_name text,
                product_id text,
                sku text NOT NULL,
                barcode text,
                barcode_norm text,
                ending text,
                availability_indicator text,
                planned_end_date date,
                coverage_days numeric(18,4),
                recommended_qty int,
                fbs_stock int DEFAULT 0,
                marketplace_side int DEFAULT 0,
                in_supply int DEFAULT 0,
                in_sale int DEFAULT 0,
                to_customer int DEFAULT 0,
                from_customer int DEFAULT 0,
                sdh_stock int DEFAULT 0,
                photo_stock int DEFAULT 0,
                defect_stock int DEFAULT 0,
                potential_per_unit numeric(18,2),
                potential_total numeric(18,2),
                UNIQUE (user_id, upload_batch_id, shop_id, sku)
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_fact_leftout_snapshot_user_batch ON {schema}.fact_leftout_snapshot (user_id, upload_batch_id)"))
        conn.commit()

        # manual_expenses — доп. расходы (вкладка «Доп. расходы»)
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.manual_expenses (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL,
                expense_date date NOT NULL,
                amount_sum numeric(18,2) NOT NULL,
                shop_id uuid,
                category text NOT NULL DEFAULT 'Прочее',
                comment text,
                name text,
                is_deleted boolean NOT NULL DEFAULT false,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_date ON {schema}.manual_expenses (user_id, expense_date)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_shop ON {schema}.manual_expenses (user_id, shop_id)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_deleted ON {schema}.manual_expenses (user_id, is_deleted)"))
        conn.commit()

        # Удалить FK на user_account, если таблицы созданы старыми миграциями (user_id без ссылки на user_account)
        for tbl in (
            "stg_sales", "stg_expenses", "stg_storage", "stg_leftout",
            "dim_shop",
            "fact_sales", "fact_expenses", "fact_storage_snapshot", "fact_leftout_snapshot",
            "map_shop_sku",
            "manual_expenses",
        ):
            conn.execute(text(f"ALTER TABLE {schema}.{tbl} DROP CONSTRAINT IF EXISTS {tbl}_user_id_fkey"))
        conn.commit()

    print("OK: таблицы для загрузки отчётов и доп. расходов созданы или уже существуют.")
    print("  dim_shop, stg_sales, stg_expenses, stg_storage, stg_leftout,")
    print("  fact_sales, fact_expenses, fact_storage_snapshot, fact_leftout_snapshot, map_shop_sku, manual_expenses")


if __name__ == "__main__":
    main()
