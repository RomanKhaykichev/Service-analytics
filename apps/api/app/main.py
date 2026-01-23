from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes import shops, products, charts, auth, debug, kpi, imports, extra_expenses
from app.settings import get_settings
import logging
from urllib.parse import urlparse

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
    return {"status": "ok", "env": settings.APP_ENV}


# Redirect root to docs (only in dev mode)
if not is_prod:
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect to API documentation."""
        return RedirectResponse(url="/docs")
