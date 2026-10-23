from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple
from collections import defaultdict

from app.config import settings
from app.models import ActualRecord, AlignedObservation, ForecastRecord, ensure_utc


def parse_date(d: str) -> date:
    """Parse YYYY-MM-DD string into a date object."""
    return date.fromisoformat(d)


def parse_time(t: str) -> time:
    """Parse HH:MM string into a time object."""
    parts = [int(p) for p in t.strip().split(":")]
    return time(hour=parts[0], minute=parts[1], second=0, tzinfo=timezone.utc)


def get_decision_cutoff(decision_date: date, cutoff_time_str: str) -> datetime:
    """
    Calculate the exact UTC datetime for a day-ahead decision cutoff on the decision date.
    Example: decision_date=2026-01-01, cutoff_time_str='09:50' -> 2026-01-01T09:50:00Z.
    """
    t = parse_time(cutoff_time_str)
    return datetime(
        year=decision_date.year,
        month=decision_date.month,
        day=decision_date.day,
        hour=t.hour,
        minute=t.minute,
        second=0,
        tzinfo=timezone.utc,
    )


def get_query_boundaries(
    decision_start_date: Optional[str] = None,
    decision_end_date: Optional[str] = None,
    lookback_days: int = 3,
) -> Dict[str, str]:
    """
    Calculate bounded query parameter strings for Elexon API requests covering January 2026.
    
    Includes a justified safety lookback for WINDFOR (e.g. 3 days before the first decision date)
    to capture multi-day forecast horizons published in late December 2025 predicting early January deliveries.
    """
    start_d = parse_date(decision_start_date or settings.DECISION_START_DATE)
    end_d = parse_date(decision_end_date or settings.DECISION_END_DATE)

    # First delivery date is start_d + 1 day (e.g., 2026-01-02)
    # Last delivery date is end_d + 1 day (e.g., 2026-02-01)
    delivery_start = start_d + timedelta(days=1)
    delivery_end = end_d + timedelta(days=1)

    # WINDFOR lookback covers forecasts published prior to first decision date
    windfor_pub_from = (start_d - timedelta(days=lookback_days)).strftime("%Y-%m-%dT00:00:00Z")
    # Latest decision occurs on end_d (e.g., 2026-01-31T23:59:59Z)
    windfor_pub_to = end_d.strftime("%Y-%m-%dT23:59:59Z")

    return {
        "fuelhh_settlement_date_from": delivery_start.isoformat(),
        "fuelhh_settlement_date_to": delivery_end.isoformat(),
        "windfor_publish_from": windfor_pub_from,
        "windfor_publish_to": windfor_pub_to,
    }


def resolve_actual_records(records: Sequence[ActualRecord]) -> Dict[datetime, float]:
    """
    Deduplicate and resolve FUELHH half-hourly actuals deterministically.
    If multiple publications exist for the same half-hourly startTime,
    the revision with the latest publishTime is selected.
    Returns: mapping of half-hour start_time (UTC) -> generation in MW.
    """
    grouped: Dict[datetime, List[ActualRecord]] = defaultdict(list)
    for r in records:
        grouped[ensure_utc(r.start_time)].append(r)

    resolved: Dict[datetime, float] = {}
    for st, recs in grouped.items():
        if len(recs) == 1:
            resolved[st] = recs[0].generation
        else:
            # Deterministic resolution: sort by publish_time ascending (None treated as earliest)
            # Pick latest valid publishTime
            sorted_recs = sorted(
                recs,
                key=lambda x: x.publish_time or datetime.min.replace(tzinfo=timezone.utc),
            )
            resolved[st] = sorted_recs[-1].generation

    return resolved


def aggregate_actuals_hourly(
    resolved_half_hours: Dict[datetime, float],
) -> Dict[datetime, float]:
    """
    Aggregate half-hourly generation outturn into complete hourly actuals.
    For each hour T:00:
      Requires both distinct half-hourly periods:
        Period 1: T:00
        Period 2: T:30
      The hourly generation is the arithmetic average: (Period 1 + Period 2) / 2.0.
      (MW is an instantaneous power rate, so average MW represents average power over the hour).
    If either half-hour reading is missing, the hour is considered incomplete and omitted.
    """
    hourly_actuals: Dict[datetime, float] = {}

    # Find all hour start timestamps present in resolved half-hours
    candidate_hours = set()
    for dt in resolved_half_hours.keys():
        if dt.minute == 0 and dt.second == 0:
            candidate_hours.add(dt)
        elif dt.minute == 30 and dt.second == 0:
            candidate_hours.add(dt - timedelta(minutes=30))

    for hour_start in sorted(candidate_hours):
        h1 = hour_start
        h2 = hour_start + timedelta(minutes=30)

        if h1 in resolved_half_hours and h2 in resolved_half_hours:
            gen1 = resolved_half_hours[h1]
            gen2 = resolved_half_hours[h2]
            # Average of the two half-hours
            hourly_actuals[hour_start] = (gen1 + gen2) / 2.0
        else:
            # Incomplete hour: excluded from completed hourly actuals
            pass

    return hourly_actuals


def select_eligible_forecasts(
    forecast_records: Sequence[ForecastRecord],
    decision_start_date: Optional[str] = None,
    decision_end_date: Optional[str] = None,
    cutoff_time_str: Optional[str] = None,
) -> Tuple[Dict[datetime, ForecastRecord], int]:
    """
    Select the latest eligible forecast revision for each target delivery period
    without lookahead bias / future-data leakage.

    Rules:
      1. For target period delivery_time T:
         - delivery_date = T.date()
         - decision_date = delivery_date - 1 day
         - If decision_date is outside [decision_start_date, decision_end_date], exclude T.
      2. decision_cutoff = datetime(decision_date at cutoff_time UTC).
      3. An eligible forecast must satisfy: publish_time <= decision_cutoff.
      4. If multiple eligible revisions exist for target T, deterministically select
         the revision with max(publish_time).
      5. Revisions published after decision_cutoff are strictly excluded.

    Returns:
      Tuple of (selected_forecasts_map: target_time -> ForecastRecord, excluded_leakage_count)
    """
    start_d = parse_date(decision_start_date or settings.DECISION_START_DATE)
    end_d = parse_date(decision_end_date or settings.DECISION_END_DATE)
    cutoff_str = cutoff_time_str or settings.DEFAULT_DECISION_CUTOFF_TIME

    # Group forecast revisions by target startTime
    grouped: Dict[datetime, List[ForecastRecord]] = defaultdict(list)
    for f in forecast_records:
        grouped[ensure_utc(f.start_time)].append(f)

    selected: Dict[datetime, ForecastRecord] = {}
    excluded_leakage_count = 0

    for target_time, revisions in grouped.items():
        delivery_date = target_time.date()
        decision_date = delivery_date - timedelta(days=1)

        # Exclude target periods outside the configured decision window
        if not (start_d <= decision_date <= end_d):
            continue

        decision_cutoff = get_decision_cutoff(decision_date, cutoff_str)

        # Filter strictly by anti-leakage rule: publish_time <= decision_cutoff
        eligible: List[ForecastRecord] = []
        for rev in revisions:
            if rev.publish_time <= decision_cutoff:
                eligible.append(rev)
            else:
                excluded_leakage_count += 1

        if eligible:
            # Deterministically select the latest revision published before or at the cutoff
            best_revision = max(eligible, key=lambda r: r.publish_time)
            selected[target_time] = best_revision

    return selected, excluded_leakage_count


def match_forecast_and_actuals(
    selected_forecasts: Dict[datetime, ForecastRecord],
    hourly_actuals: Dict[datetime, float],
    decision_start_date: Optional[str] = None,
    decision_end_date: Optional[str] = None,
    cutoff_time_str: Optional[str] = None,
) -> Tuple[List[AlignedObservation], int, int]:
    """
    Match eligible day-ahead forecasts with complete hourly actuals.
    
    Returns:
      Tuple of:
        - List of AlignedObservation
        - missing_actual_count (forecast present, but actual missing or incomplete)
        - missing_forecast_count (in-scope actual present, but no eligible forecast available)
    """
    cutoff_str = cutoff_time_str or settings.DEFAULT_DECISION_CUTOFF_TIME
    aligned: List[AlignedObservation] = []
    missing_actual_count = 0
    missing_forecast_count = 0

    # Collect all unique candidate delivery hours across both datasets
    all_target_hours = sorted(set(selected_forecasts.keys()) | set(hourly_actuals.keys()))

    for target_time in all_target_hours:
        has_forecast = target_time in selected_forecasts
        has_actual = target_time in hourly_actuals

        if has_forecast and has_actual:
            forecast = selected_forecasts[target_time]
            actual_gen = hourly_actuals[target_time]

            delivery_date = target_time.date()
            decision_date = delivery_date - timedelta(days=1)
            cutoff = get_decision_cutoff(decision_date, cutoff_str)

            error_mw = forecast.generation - actual_gen
            aligned.append(
                AlignedObservation(
                    target_time=target_time,
                    delivery_date=delivery_date.isoformat(),
                    decision_date=decision_date.isoformat(),
                    decision_cutoff=cutoff,
                    forecast_generation=forecast.generation,
                    actual_generation=actual_gen,
                    forecast_publish_time=forecast.publish_time,
                    error_mw=error_mw,
                    absolute_error_mw=abs(error_mw),
                )
            )
        elif has_forecast and not has_actual:
            missing_actual_count += 1
        elif not has_forecast and has_actual:
            missing_forecast_count += 1

    return aligned, missing_actual_count, missing_forecast_count
