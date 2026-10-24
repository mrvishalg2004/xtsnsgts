import math
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ActualRecord(BaseModel):
    """Normalized actual wind-generation record from FUELHH."""

    start_time: datetime
    publish_time: Optional[datetime] = None
    generation: float
    settlement_date: Optional[str] = None
    settlement_period: Optional[int] = None
    fuel_type: str = "WIND"

    @field_validator("start_time", "publish_time", mode="after")
    @classmethod
    def validate_utc_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            return ensure_utc(v)
        return v

    @field_validator("generation", mode="after")
    @classmethod
    def validate_finite_generation(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("generation must be a finite number (cannot be NaN or Inf)")
        return v


class ForecastRecord(BaseModel):
    """Normalized wind-generation forecast record from WINDFOR."""

    start_time: datetime
    publish_time: datetime
    generation: float

    @field_validator("start_time", "publish_time", mode="after")
    @classmethod
    def validate_utc_tz(cls, v: datetime) -> datetime:
        return ensure_utc(v)

    @field_validator("generation", mode="after")
    @classmethod
    def validate_finite_generation(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("generation must be a finite number (cannot be NaN or Inf)")
        return v


class AlignedObservation(BaseModel):
    """A target delivery period with matched day-ahead forecast and actual outturn."""

    target_time: datetime
    delivery_date: str
    decision_date: str
    decision_cutoff: datetime
    forecast_generation: float
    actual_generation: float
    forecast_publish_time: datetime
    error_mw: float = Field(
        ...,
        description="Forecast error in MW: forecast_generation - actual_generation",
    )
    absolute_error_mw: float = Field(
        ...,
        description="Absolute forecast error in MW: abs(error_mw)",
    )

    @field_validator("target_time", "decision_cutoff", "forecast_publish_time", mode="after")
    @classmethod
    def validate_utc_tz(cls, v: datetime) -> datetime:
        return ensure_utc(v)

    @field_validator("forecast_generation", "actual_generation", "error_mw", "absolute_error_mw", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Observation generation and error values must be finite numbers")
        return v


class EvaluationMetrics(BaseModel):
    """Statistical forecast accuracy evaluation metrics."""

    mae: Optional[float] = Field(
        None, description="Mean Absolute Error in MW"
    )
    rmse: Optional[float] = Field(
        None, description="Root Mean Squared Error in MW"
    )
    mbe: Optional[float] = Field(
        None, description="Mean Bias Error in MW (positive = over-forecast)"
    )
    wape: Optional[float] = Field(
        None, description="Weighted Absolute Percentage Error in percent (%)"
    )
    matched_count: int = Field(
        0, description="Number of complete matched observations evaluated"
    )
    missing_actual_count: int = Field(
        0, description="Number of target intervals missing valid actual outturn"
    )
    missing_forecast_count: int = Field(
        0, description="Number of target intervals missing an eligible forecast before cutoff"
    )

    @field_validator("mae", "rmse", "mbe", "wape", mode="after")
    @classmethod
    def validate_finite_metrics(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("Evaluation metric values must be finite numbers")
        return v


class FilterParameters(BaseModel):
    """Normalized query filters applied to evaluation."""

    decision_start_date: str
    decision_end_date: str
    cutoff_time: str
    delivery_start_date: str
    delivery_end_date: str


class DataQualityCounts(BaseModel):
    """Data processing counters describing actual evaluation execution."""

    raw_fuelhh_count: int = Field(..., description="Total raw FUELHH actual records retrieved")
    raw_windfor_count: int = Field(..., description="Total raw WINDFOR forecast records retrieved")
    selected_forecast_count: int = Field(..., description="Distinct target hours with an eligible forecast before cutoff")
    excluded_leakage_count: int = Field(..., description="Forecast revisions excluded due to publishTime > cutoff")
    hourly_actual_count: int = Field(..., description="Complete hourly actual periods constructed from pairs of half-hours")
    matched_count: int = Field(..., description="Complete hourly periods with both eligible forecast and actual")
    missing_actual_count: int = Field(..., description="Delivery hours having forecast but lacking complete actual")
    missing_forecast_count: int = Field(..., description="Delivery hours having complete actual but lacking forecast before cutoff")
    missing_both_count: int = Field(..., description="Delivery hours within scope missing both forecast and complete actual")


class CacheMetadata(BaseModel):
    """Metadata regarding cache status and upstream data freshness."""

    cached: bool
    data_retrieval_timestamp: Optional[datetime] = None
    cache_ttl_seconds: int


class SummaryMetricsResponse(BaseModel):
    """Payload for GET /api/summary-metrics."""

    status: str = "ok"
    filters: FilterParameters
    metrics: EvaluationMetrics
    data_quality: DataQualityCounts
    cache_metadata: CacheMetadata


class TimeseriesRecord(BaseModel):
    """Hourly observation or missing period record for GET /api/timeseries."""

    target_start_time: datetime
    delivery_date: str
    decision_date: str
    decision_cutoff: datetime
    forecast_publish_time: Optional[datetime] = None
    forecast_generation_mw: Optional[float] = None
    actual_generation_mw: Optional[float] = None
    error_mw: Optional[float] = None
    absolute_error_mw: Optional[float] = None
    availability_status: str = Field(
        ...,
        description="'matched' | 'missing_forecast' | 'missing_actual' | 'missing_both'",
    )

    @field_validator("target_start_time", "decision_cutoff", "forecast_publish_time", mode="after")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            return ensure_utc(v)
        return v


class TimeseriesResponse(BaseModel):
    """Payload for GET /api/timeseries."""

    status: str = "ok"
    filters: FilterParameters
    total_periods: int
    records: list[TimeseriesRecord]
    cache_metadata: CacheMetadata


class RevisionItem(BaseModel):
    """A single WINDFOR publication run revision for a target startTime."""

    publish_time: datetime
    forecast_generation_mw: float
    is_eligible: bool
    is_selected: bool
    status_reason: str = Field(
        ...,
        description="'selected' | 'eligible_but_not_selected' | 'published_after_cutoff'",
    )

    @field_validator("publish_time", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)


class RevisionsResponse(BaseModel):
    """Payload for GET /api/revisions."""

    status: str = "ok"
    target_start_time: datetime
    delivery_date: str
    decision_date: str
    decision_cutoff: datetime
    total_revisions: int
    eligible_revisions_count: int
    selected_revision: Optional[RevisionItem] = None
    revisions: list[RevisionItem]
    cache_metadata: CacheMetadata

    @field_validator("target_start_time", "decision_cutoff", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)
