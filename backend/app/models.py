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


class ForecastRecord(BaseModel):
    """Normalized wind-generation forecast record from WINDFOR."""

    start_time: datetime
    publish_time: datetime
    generation: float

    @field_validator("start_time", "publish_time", mode="after")
    @classmethod
    def validate_utc_tz(cls, v: datetime) -> datetime:
        return ensure_utc(v)


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
