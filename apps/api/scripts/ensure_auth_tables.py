"""
Создаёт схему app и таблицы для авторизации (users, auth_identities, refresh_tokens, verification_codes)
в той же базе, к которой подключается API (из .env в apps/api).
Запуск из корня репозитория или из apps/api:
  cd apps/api && .venv\Scripts\activate && python scripts/ensure_auth_tables.py
"""
import sys
from pathlib import Path

# Чтобы подхватить app.settings из apps/api
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

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.users (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                email varchar(255) UNIQUE,
                full_name varchar(255),
                phone varchar(50) UNIQUE,
                is_active boolean NOT NULL DEFAULT true,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_users_email ON {schema}.users (email)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_users_phone ON {schema}.users (phone)"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS admin_notes text"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS plan varchar(50) NOT NULL DEFAULT 'trial'"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS last_login_at timestamptz"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS phone_verified_at timestamptz"))
        conn.execute(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS allowed_shops text"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.auth_identities (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                provider varchar(50) NOT NULL,
                identifier varchar(255) NOT NULL,
                password_hash varchar(255),
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_auth_identities_user_id ON {schema}.auth_identities (user_id)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_auth_identities_identifier ON {schema}.auth_identities (identifier)"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.refresh_tokens (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                token_hash varchar(255) NOT NULL UNIQUE,
                revoked_at timestamptz,
                expires_at timestamptz NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON {schema}.refresh_tokens (user_id)"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON {schema}.refresh_tokens (token_hash)"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.verification_codes (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid REFERENCES {schema}.users(id) ON DELETE CASCADE,
                channel varchar(50) NOT NULL,
                destination varchar(255) NOT NULL,
                code_hash varchar(255) NOT NULL,
                expires_at timestamptz NOT NULL,
                consumed_at timestamptz,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_verification_codes_user_id ON {schema}.verification_codes (user_id)"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.otp_attempts (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid REFERENCES {schema}.users(id) ON DELETE CASCADE,
                phone_normalized varchar(64) NOT NULL,
                kind varchar(32) NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS ix_otp_attempts_phone_created
            ON {schema}.otp_attempts (phone_normalized, created_at DESC)
        """))
        conn.commit()

        # Таблица для загрузки отчётов (create_batch в imports.py)
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.upload_batch (
                upload_batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                status varchar(50) NOT NULL DEFAULT 'processing',
                is_current boolean NOT NULL DEFAULT false
            )
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_upload_batch_user_id ON {schema}.upload_batch (user_id)"))
        conn.execute(text(f"ALTER TABLE {schema}.upload_batch ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()"))
        conn.execute(text(f"ALTER TABLE {schema}.upload_batch ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_upload_batch_created_at ON {schema}.upload_batch (created_at)"))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.login_events (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                logged_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS ix_login_events_logged_at ON {schema}.login_events (logged_at)
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS ix_login_events_user_id ON {schema}.login_events (user_id)
        """))
        conn.commit()
        # Один раз восстановить счётчик из last_login_at, если событий ещё нет
        conn.execute(text(f"""
            INSERT INTO {schema}.login_events (user_id, logged_at)
            SELECT u.id, u.last_login_at
            FROM {schema}.users u
            WHERE u.last_login_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM {schema}.login_events le WHERE le.user_id = u.id
              )
        """))
        conn.commit()

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.training_page_views (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS ix_training_page_views_created_at
            ON {schema}.training_page_views (created_at)
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.tariff_payment_opens (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE CASCADE,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS ix_tariff_payment_opens_created_at
            ON {schema}.tariff_payment_opens (created_at)
        """))
        conn.commit()

        # Если upload_batch уже была создана с FK на user_account — перепривязать на app.users
        conn.execute(text(f"ALTER TABLE {schema}.upload_batch DROP CONSTRAINT IF EXISTS upload_batch_user_id_fkey"))
        conn.commit()
        # Удалить батчи с user_id, которых нет в app.users (иначе ADD CONSTRAINT упадёт)
        conn.execute(text(f"""
            DELETE FROM {schema}.upload_batch
            WHERE user_id NOT IN (SELECT id FROM {schema}.users)
        """))
        conn.commit()
        conn.execute(text(f"""
            ALTER TABLE {schema}.upload_batch
            ADD CONSTRAINT upload_batch_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES {schema}.users(id) ON DELETE CASCADE
        """))
        conn.commit()

    # Убрать FK manual_expenses.user_id -> user_account, если есть (доп. расходы привязаны к app.users)
    try:
        conn.execute(text(f"""
            ALTER TABLE {schema}.manual_expenses
            DROP CONSTRAINT IF EXISTS manual_expenses_user_id_fkey
        """))
        conn.commit()
    except Exception as e:
        # Таблица может не существовать или constraint уже снят
        if "does not exist" not in str(e).lower():
            print(f"  (manual_expenses FK drop skipped: {e})")
        conn.rollback()

    print("OK: схема и таблицы авторизации и загрузки созданы (или уже существуют).")
    print(
        "  Таблицы:",
        f"{schema}.users",
        f"{schema}.auth_identities",
        f"{schema}.refresh_tokens",
        f"{schema}.verification_codes",
        f"{schema}.upload_batch",
        f"{schema}.login_events",
    )


if __name__ == "__main__":
    main()
