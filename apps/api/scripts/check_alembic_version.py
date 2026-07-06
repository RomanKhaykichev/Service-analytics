from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"], connect_args={"connect_timeout": 5})
with engine.connect() as c:
    print("alembic:", c.execute(text("SELECT version_num FROM app.alembic_version")).fetchall())
    for col in ("trial_display_shop", "allowed_shops", "shop_raw"):
        row = c.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='users' AND column_name=:c"
            ),
            {"c": col},
        ).fetchone()
        print(f"users.{col}:", "yes" if row else "no")
    row = c.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='fact_expenses' AND column_name='shop_id'"
        )
    ).fetchone()
    print("fact_expenses.shop_id:", "yes" if row else "no")
