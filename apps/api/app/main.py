from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import shops, products, charts, auth, debug

app = FastAPI(
    title="Service Analytics API",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(shops.router, prefix="/api", tags=["shops"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(charts.router, prefix="/api", tags=["charts"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}
