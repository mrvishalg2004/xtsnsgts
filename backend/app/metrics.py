import math
from typing import List, Optional, Sequence
from app.models import AlignedObservation, EvaluationMetrics


def calculate_metrics(
    observations: Sequence[AlignedObservation],
    missing_actual_count: int = 0,
    missing_forecast_count: int = 0,
) -> EvaluationMetrics:
    """
    Calculate statistical forecast evaluation metrics from matched observations.

    Definitions:
      - error_mw = forecast_generation - actual_generation
      - MAE  = mean(abs(forecast - actual)) [MW]
      - RMSE = sqrt(mean((forecast - actual)^2)) [MW]
      - MBE  = mean(forecast - actual) [MW] (positive means forecast was higher than actual)
      - WAPE = sum(abs(forecast - actual)) / sum(abs(actual)) * 100 [%]

    Edge cases:
      - Empty matched observations: returns None for numeric metrics and matched_count=0.
      - Zero sum of actuals: returns WAPE as None (null) to prevent division by zero.
      - Valid zero generation values are preserved and included in calculations.
    """
    n = len(observations)
    if n == 0:
        return EvaluationMetrics(
            mae=None,
            rmse=None,
            mbe=None,
            wape=None,
            matched_count=0,
            missing_actual_count=missing_actual_count,
            missing_forecast_count=missing_forecast_count,
        )

    # Verify all observations contain strictly finite values
    for obs in observations:
        if (
            not math.isfinite(obs.forecast_generation)
            or not math.isfinite(obs.actual_generation)
            or not math.isfinite(obs.error_mw)
        ):
            raise ValueError(
                f"Non-finite generation or error encountered in observation for target {obs.target_time}"
            )

    errors = [obs.forecast_generation - obs.actual_generation for obs in observations]
    abs_errors = [abs(e) for e in errors]
    actuals = [obs.actual_generation for obs in observations]

    # Full floating-point precision
    mae = sum(abs_errors) / n
    mse = sum(e ** 2 for e in errors) / n
    rmse = math.sqrt(mse)
    mbe = sum(errors) / n

    if not math.isfinite(mae) or not math.isfinite(rmse) or not math.isfinite(mbe):
        raise ValueError("Computed non-finite evaluation metrics")

    sum_actuals = sum(abs(a) for a in actuals)
    if sum_actuals == 0.0:
        wape: Optional[float] = None
    else:
        wape = (sum(abs_errors) / sum_actuals) * 100.0
        if not math.isfinite(wape):
            raise ValueError("Computed non-finite WAPE metric")

    return EvaluationMetrics(
        mae=mae,
        rmse=rmse,
        mbe=mbe,
        wape=wape,
        matched_count=n,
        missing_actual_count=missing_actual_count,
        missing_forecast_count=missing_forecast_count,
    )
