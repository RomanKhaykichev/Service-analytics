from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from app.routes import shops, kpi, charts, products


class UTF8ORJSONResponse(ORJSONResponse):
    """ORJSONResponse with explicit charset=utf-8 in Content-Type."""
    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Service Analytics API",
    version="1.0.0",
    default_response_class=UTF8ORJSONResponse
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(shops.router, prefix="/api", tags=["shops"])
app.include_router(kpi.router, prefix="/api", tags=["kpi"])
app.include_router(charts.router, prefix="/api", tags=["charts"])
app.include_router(products.router, prefix="/api", tags=["products"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}
