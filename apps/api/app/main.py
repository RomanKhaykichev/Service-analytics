from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes import shops, products, charts, auth, debug, kpi, imports
from app.settings import get_settings

settings = get_settings()

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
