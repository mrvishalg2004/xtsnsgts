from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="UK Wind-Generation Forecast Evaluation & Day-Ahead Electricity Purchasing Analytics API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local Vite frontend and configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint confirming backend service operational status."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["System"])
async def root():
    """Root redirect / discovery information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": "/api/health",
        "status": "online",
    }
