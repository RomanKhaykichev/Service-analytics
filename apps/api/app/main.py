from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes import shops, products, charts, auth, debug, kpi, imports, extra_expenses
from app.settings import get_settings
from app.db import engine
import logging
from urllib.parse import urlparse
from sqlalchemy import text

logger = logging.getLogger(__name__)
settings = get_settings()

# Log database connection info at startup (without password)
def log_database_info():
    """Log database connection info without exposing password."""
    try:
        parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"))
        logger.info("=" * 60)
        logger.info("Database Connection Info:")
        logger.info(f"  Host: {parsed.hostname or 'localhost'}")
        logger.info(f"  Port: {parsed.port or 5432}")
        logger.info(f"  Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
        logger.info(f"  User: {parsed.username or 'N/A'}")
        logger.info(f"  Schema: {settings.DB_SCHEMA}")
        logger.info(f"  Password: {'***' if parsed.password else 'N/A'}")
        logger.info("=" * 60)
    except Exception as e:
        logger.warning(f"Could not parse DATABASE_URL: {e}")

log_database_info()


def check_alembic_migrations():
    """Check Alembic migration status and log warnings if needed."""
    try:
        with engine.connect() as conn:
            # Check if alembic_version table exists
            version_table_query = text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = 'alembic_version'
                ORDER BY table_schema
            """)
            version_tables = conn.execute(version_table_query).fetchall()
            
            if not version_tables:
                logger.error("=" * 60)
                logger.error("⚠️  MIGRATION CHECK FAILED: alembic_version table not found!")
                logger.error("=" * 60)
                logger.error("This means no migrations have been applied to this database.")
                logger.error("")
                logger.error("To fix this, run migrations:")
                logger.error("  python -m alembic upgrade head")
                logger.error("  # Or use scripts:")
                logger.error("  .\\scripts\\migrate.ps1  (Windows)")
                logger.error("  ./scripts/migrate.sh     (Linux/Mac)")
                logger.error("=" * 60)
                return
            
            # Get version from expected schema
            schema = settings.DB_SCHEMA
            version_in_schema = [t for t in version_tables if t[0] == schema]
            
            if version_in_schema:
                version_query = text(f"""
                    SELECT version_num
                    FROM {schema}.alembic_version
                    ORDER BY version_num DESC
                    LIMIT 1
                """)
                result = conn.execute(version_query)
                current_revision = result.scalar()
                
                if current_revision:
                    logger.info(f"✅ Current Alembic revision: {current_revision}")
                else:
                    logger.warning("⚠️  alembic_version table exists but is empty (no revision recorded)")
                    logger.warning("Run: python -m alembic upgrade head")
            else:
                logger.warning(f"⚠️  alembic_version table not found in schema '{schema}'")
                logger.warning("Available locations:")
                for schema_name, table_name in version_tables:
                    logger.warning(f"  - {schema_name}.{table_name}")
                logger.warning("")
                logger.warning("Run: python -m alembic upgrade head")
                
            # Check critical table existence
            critical_table_query = text(f"""
                SELECT to_regclass('{schema}.map_shop_barcode')
            """)
            table_exists = conn.execute(critical_table_query).scalar()
            
            if not table_exists:
                logger.error("=" * 60)
                logger.error("⚠️  CRITICAL TABLE MISSING: app.map_shop_barcode")
                logger.error("=" * 60)
                logger.error("This table is required for imports to work!")
                logger.error("")
                logger.error("To fix this, run migrations:")
                logger.error("  python -m alembic upgrade head")
                logger.error("=" * 60)
            else:
                logger.info("✅ Critical table 'app.map_shop_barcode' exists")
                
    except Exception as e:
        logger.warning(f"Could not check Alembic migrations: {e}")
        logger.warning("This might indicate a database connection issue.")


# Check migrations on startup
check_alembic_migrations()

# Determine if documentation should be enabled
is_prod = settings.APP_ENV == "prod"
docs_config = {
    "docs_url": None if is_prod else "/docs",
    "redoc_url": None if is_prod else "/redoc",
    "openapi_url": None if is_prod else "/openapi.json",
}

app = FastAPI(
    title="Service Analytics API",
    version="1.0.0",
    **docs_config
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-User-Id", "Content-Type", "Authorization", "*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(shops.router, prefix="/api", tags=["shops"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(charts.router, prefix="/api", tags=["charts"])
app.include_router(kpi.router, prefix="/api", tags=["kpi"])
app.include_router(debug.router, prefix="/api", tags=["debug"])
app.include_router(imports.router, prefix="/api", tags=["imports"])
app.include_router(extra_expenses.router, prefix="/api", tags=["extra-expenses"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}


@app.get("/api/health")
async def api_health():
    """API health check endpoint."""
    return {"ok": True}


# Redirect root to docs (only in dev mode)
if not is_prod:
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect to API documentation."""
        return RedirectResponse(url="/docs")
