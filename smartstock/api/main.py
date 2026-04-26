"""
SmartStock FastAPI application entry point.

Run with:
    uvicorn smartstock.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smartstock.api.routes import abc, forecast, optimize

app = FastAPI(
    title="SmartStock API",
    description="AI-powered demand forecasting and inventory optimisation API.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8051",
        "http://127.0.0.1:8051",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router, prefix="/api", tags=["Forecasting"])
app.include_router(optimize.router, prefix="/api", tags=["Optimization"])
app.include_router(abc.router, prefix="/api", tags=["Inventory Classification"])


@app.get("/health", tags=["Health"])
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "service": "SmartStock API"}
