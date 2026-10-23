import math
from datetime import datetime, timezone
import pytest

from app.metrics import calculate_metrics
from app.models import AlignedObservation


def make_observation(
    forecast: float,
    actual: float,
    target_hour: str = "2026-01-02T10:00:00Z",
) -> AlignedObservation:
    dt = datetime.fromisoformat(target_hour.replace("Z", "+00:00"))
    err = forecast - actual
    return AlignedObservation(
        target_time=dt,
        delivery_date="2026-01-02",
        decision_date="2026-01-01",
        decision_cutoff=datetime(2026, 1, 1, 9, 50, tzinfo=timezone.utc),
        forecast_generation=forecast,
        actual_generation=actual,
        forecast_publish_time=datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc),
        error_mw=err,
        absolute_error_mw=abs(err),
    )


def test_hand_calculated_metrics_precision():
    """Verify MAE, RMSE, MBE, and WAPE against exact hand-calculated expected values."""
    # Obs 1: Forecast=100, Actual=80 -> err=+20
    # Obs 2: Forecast=60,  Actual=70 -> err=-10
    obs = [
        make_observation(100.0, 80.0, "2026-01-02T10:00:00Z"),
        make_observation(60.0, 70.0, "2026-01-02T11:00:00Z"),
    ]

    metrics = calculate_metrics(obs)

    assert metrics.matched_count == 2
    assert metrics.mae == 15.0
    assert math.isclose(metrics.rmse, math.sqrt(250.0), rel_tol=1e-9)
    assert metrics.mbe == 5.0  # Positive bias: over-forecast
    assert metrics.wape == 20.0  # (30 / 150) * 100


def test_negative_bias():
    """Verify MBE accurately reflects systematic under-forecasting."""
    obs = [
        make_observation(50.0, 70.0, "2026-01-02T10:00:00Z"),  # err = -20
        make_observation(30.0, 50.0, "2026-01-02T11:00:00Z"),  # err = -20
    ]
    metrics = calculate_metrics(obs)
    assert metrics.mbe == -20.0
    assert metrics.mae == 20.0


def test_zero_actual_generation_preserves_validity_and_handles_wape():
    """
    Valid zero-generation readings must be preserved, and zero denominator in WAPE
    must return None without crashing or fabricating a 0% error.
    """
    obs = [
        make_observation(15.0, 0.0, "2026-01-02T10:00:00Z"),  # err = +15, actual = 0
        make_observation(0.0, 0.0, "2026-01-02T11:00:00Z"),   # err = 0,   actual = 0
    ]

    metrics = calculate_metrics(obs)

    assert metrics.matched_count == 2
    assert metrics.mae == 7.5
    assert math.isclose(metrics.rmse, math.sqrt(225.0 / 2.0), rel_tol=1e-9)
    assert metrics.mbe == 7.5
    assert metrics.wape is None  # Division by zero avoided; returns None


def test_empty_observations():
    """Empty matched dataset returns None for all numeric metrics and matched_count=0."""
    metrics = calculate_metrics([], missing_actual_count=5, missing_forecast_count=2)

    assert metrics.matched_count == 0
    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.mbe is None
    assert metrics.wape is None
    assert metrics.missing_actual_count == 5
    assert metrics.missing_forecast_count == 2
