from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import logging
import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.analysis_service import AnalysisService
from app.config import settings
from app.elexon_client import ElexonDataValidationError, ElexonHTTPError
from app.models import (
    RevisionsResponse,
    SummaryMetricsResponse,
    TimeseriesResponse,
    ensure_utc,
)

logger = logging.getLogger("wind_forecast_insights")
logging.basicConfig(level=logging.INFO)

# Global analysis service instance
analysis_service = AnalysisService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle and HTTP client resources."""
    logger.info("Initializing Wind Forecast Insights application")
    yield
    logger.info("Shutting down Wind Forecast Insights application - closing resources")
    analysis_service.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="UK Wind-Generation Forecast Evaluation & Day-Ahead Electricity Purchasing Analytics API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_date_range(start_str: str, end_str: str) -> tuple[date, date]:
    """Validate decision date range strictly within January 1–31, 2026."""
    try:
        start_d = date.fromisoformat(start_str)
        end_d = date.fromisoformat(end_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Expected YYYY-MM-DD.",
        )

    min_d = date(2026, 1, 1)
    max_d = date(2026, 1, 31)

    if not (min_d <= start_d <= max_d):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"decision_start_date '{start_str}' must be within January 2026 (2026-01-01 to 2026-01-31).",
        )

    if not (min_d <= end_d <= max_d):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"decision_end_date '{end_str}' must be within January 2026 (2026-01-01 to 2026-01-31).",
        )

    if start_d > end_d:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"decision_start_date '{start_str}' cannot be after decision_end_date '{end_str}'.",
        )

    return start_d, end_d


def validate_cutoff_time(cutoff_str: str) -> str:
    """Validate cutoff time format HH:MM in UTC 24-hour clock."""
    if not isinstance(cutoff_str, str) or not re.match(r"^\d{2}:\d{2}$", cutoff_str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cutoff_time '{cutoff_str}'. Expected HH:MM in 24-hour UTC format (e.g. 09:50).",
        )
    hours, minutes = [int(p) for p in cutoff_str.split(":")]
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"cutoff_time '{cutoff_str}' has invalid hours (0-23) or minutes (0-59).",
        )
    return cutoff_str


def validate_target_start_time(target_str: str) -> datetime:
    """Validate target delivery timestamp is hourly aligned and within delivery horizon."""
    try:
        clean_str = target_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        utc_dt = ensure_utc(dt)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target_start_time '{target_str}'. Expected ISO-8601 UTC timestamp (e.g. 2026-01-02T12:00:00Z).",
        )

    # Must be aligned to hourly interval (minute=0, second=0)
    if utc_dt.minute != 0 or utc_dt.second != 0 or utc_dt.microsecond != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"target_start_time '{target_str}' must be aligned to an hourly boundary (:00:00).",
        )

    min_target = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    max_target = datetime(2026, 2, 1, 23, 0, 0, tzinfo=timezone.utc)

    if not (min_target <= utc_dt <= max_target):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"target_start_time '{target_str}' is out of scope. "
                "Delivery horizon for January 2026 purchasing decisions is 2026-01-02T00:00:00Z to 2026-02-01T23:00:00Z."
            ),
        )

    return utc_dt


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
    """Root discovery information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": [
            "/api/health",
            "/api/summary-metrics",
            "/api/timeseries",
            "/api/revisions",
        ],
        "status": "online",
    }


@app.get(
    "/api/summary-metrics",
    response_model=SummaryMetricsResponse,
    tags=["Analysis"],
    summary="Get aggregated forecast evaluation metrics",
)
async def get_summary_metrics(
    decision_start_date: str = Query("2026-01-01", description="Start decision date YYYY-MM-DD (2026-01-01 to 2026-01-31)"),
    decision_end_date: str = Query("2026-01-31", description="End decision date YYYY-MM-DD (2026-01-01 to 2026-01-31)"),
    cutoff_time: str = Query("09:50", description="Day-Ahead decision cutoff time HH:MM (UTC)"),
):
    """
    Evaluate day-ahead wind generation forecasts against actuals across a decision date window.
    Calculates MAE, RMSE, MBE, and WAPE with anti-leakage forecast revision selection.
    """
    validate_date_range(decision_start_date, decision_end_date)
    validate_cutoff_time(cutoff_time)

    try:
        summary, _ = analysis_service.evaluate(
            decision_start_date=decision_start_date,
            decision_end_date=decision_end_date,
            cutoff_time=cutoff_time,
        )
        return summary
    except (ElexonHTTPError, ElexonDataValidationError) as exc:
        logger.error(f"Upstream Elexon error in /api/summary-metrics: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve or parse upstream Elexon data.",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error in /api/summary-metrics: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating forecast metrics.",
        ) from exc


@app.get(
    "/api/timeseries",
    response_model=TimeseriesResponse,
    tags=["Analysis"],
    summary="Get hourly timeseries of forecasts and actuals",
)
async def get_timeseries(
    decision_start_date: str = Query("2026-01-01", description="Start decision date YYYY-MM-DD (2026-01-01 to 2026-01-31)"),
    decision_end_date: str = Query("2026-01-31", description="End decision date YYYY-MM-DD (2026-01-01 to 2026-01-31)"),
    cutoff_time: str = Query("09:50", description="Day-Ahead decision cutoff time HH:MM (UTC)"),
):
    """
    Retrieve chronological hourly timeseries records comparing day-ahead forecasts
    with actual generation across the corresponding delivery dates.
    """
    validate_date_range(decision_start_date, decision_end_date)
    validate_cutoff_time(cutoff_time)

    try:
        _, timeseries = analysis_service.evaluate(
            decision_start_date=decision_start_date,
            decision_end_date=decision_end_date,
            cutoff_time=cutoff_time,
        )
        return timeseries
    except (ElexonHTTPError, ElexonDataValidationError) as exc:
        logger.error(f"Upstream Elexon error in /api/timeseries: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve or parse upstream Elexon data.",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error in /api/timeseries: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while building timeseries data.",
        ) from exc


@app.get(
    "/api/revisions",
    response_model=RevisionsResponse,
    tags=["Analysis"],
    summary="Inspect forecast revisions for a specific delivery hour",
)
async def get_revisions(
    target_start_time: str = Query(..., description="Target delivery startTime in ISO-8601 UTC format (e.g. 2026-01-02T12:00:00Z)"),
    cutoff_time: str = Query("09:50", description="Day-Ahead decision cutoff time HH:MM (UTC)"),
):
    """
    Inspect all historical WINDFOR revisions published for a specific target delivery hour,
    identifying eligible vs post-cutoff revisions and the selected day-ahead benchmark.
    """
    target_dt = validate_target_start_time(target_start_time)
    validate_cutoff_time(cutoff_time)

    try:
        revisions = analysis_service.get_revisions(
            target_start_time=target_dt,
            cutoff_time=cutoff_time,
        )
        return revisions
    except (ElexonHTTPError, ElexonDataValidationError) as exc:
        logger.error(f"Upstream Elexon error in /api/revisions: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve or parse upstream Elexon forecast revisions.",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error in /api/revisions: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while inspecting forecast revisions.",
        ) from exc
