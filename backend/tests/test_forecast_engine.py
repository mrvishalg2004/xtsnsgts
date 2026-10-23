from datetime import date, datetime, timezone
import pytest

from app.forecast_engine import (
    aggregate_actuals_hourly,
    get_decision_cutoff,
    get_query_boundaries,
    match_forecast_and_actuals,
    resolve_actual_records,
    select_eligible_forecasts,
)
from app.metrics import calculate_metrics
from app.models import ActualRecord, ForecastRecord


def utc_dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def test_decision_cutoff_derivation():
    """Verify exact derivation of cutoff datetime from decision date and HH:MM string."""
    cutoff = get_decision_cutoff(date(2026, 1, 1), "09:50")
    assert cutoff == datetime(2026, 1, 1, 9, 50, 0, tzinfo=timezone.utc)

    cutoff_alt = get_decision_cutoff(date(2026, 1, 15), "11:00")
    assert cutoff_alt == datetime(2026, 1, 15, 11, 0, 0, tzinfo=timezone.utc)


def test_query_boundaries_include_december_lookback():
    """Verify that query range for WINDFOR looks back into late December to catch horizon runs."""
    bounds = get_query_boundaries("2026-01-01", "2026-01-31", lookback_days=3)
    assert bounds["fuelhh_settlement_date_from"] == "2026-01-02"
    assert bounds["fuelhh_settlement_date_to"] == "2026-02-01"
    assert bounds["windfor_publish_from"] == "2025-12-29T00:00:00Z"
    assert bounds["windfor_publish_to"] == "2026-01-31T23:59:59Z"


def test_december_publication_eligible_for_early_january_delivery():
    """A forecast published on Dec 31 covering Jan 2 delivery must be eligible if before cutoff."""
    target_hour = utc_dt("2026-01-02T12:00:00Z")  # Decision date: 2026-01-01, Cutoff: 09:50 UTC
    recs = [
        ForecastRecord(
            start_time=target_hour,
            publish_time=utc_dt("2025-12-31T20:00:00Z"),
            generation=14000.0,
        )
    ]
    selected, excluded = select_eligible_forecasts(recs, "2026-01-01", "2026-01-31", "09:50")
    assert target_hour in selected
    assert selected[target_hour].generation == 14000.0
    assert excluded == 0


def test_forecast_cutoff_boundary_inclusion_and_exclusion():
    """
    Test exact cutoff boundaries:
    - 1 minute before cutoff -> eligible
    - Exactly at cutoff -> eligible
    - 1 second after cutoff -> strictly excluded
    """
    target_hour = utc_dt("2026-01-02T14:00:00Z")
    # Decision date: 2026-01-01. Cutoff: 09:50:00Z

    # Just before cutoff (09:49:00Z)
    rec_before = ForecastRecord(
        start_time=target_hour,
        publish_time=utc_dt("2026-01-01T09:49:00Z"),
        generation=12000.0,
    )
    # Exactly at cutoff (09:50:00Z)
    rec_exact = ForecastRecord(
        start_time=target_hour,
        publish_time=utc_dt("2026-01-01T09:50:00Z"),
        generation=12500.0,
    )
    # Just after cutoff (09:50:01Z)
    rec_after = ForecastRecord(
        start_time=target_hour,
        publish_time=utc_dt("2026-01-01T09:50:01Z"),
        generation=13000.0,
    )

    # 1. Just before cutoff is selected
    sel, excl = select_eligible_forecasts([rec_before], "2026-01-01", "2026-01-31", "09:50")
    assert sel[target_hour].generation == 12000.0
    assert excl == 0

    # 2. Exactly at cutoff is eligible and supersedes earlier revision
    sel, excl = select_eligible_forecasts([rec_before, rec_exact], "2026-01-01", "2026-01-31", "09:50")
    assert sel[target_hour].generation == 12500.0
    assert excl == 0

    # 3. Post-cutoff revision is excluded and does not overwrite the cutoff-eligible revision
    sel, excl = select_eligible_forecasts([rec_before, rec_exact, rec_after], "2026-01-01", "2026-01-31", "09:50")
    assert sel[target_hour].generation == 12500.0  # Retains the 09:50:00Z revision!
    assert excl == 1


def test_out_of_scope_dates_are_excluded():
    """
    Target delivery periods with decision dates outside Jan 1 - Jan 31 must be excluded.
    e.g. Delivery on Jan 1 has decision Dec 31 (excluded).
    Delivery on Feb 2 has decision Feb 1 (excluded).
    """
    jan_1_delivery = utc_dt("2026-01-01T12:00:00Z")  # Decision: 2025-12-31
    feb_2_delivery = utc_dt("2026-02-02T12:00:00Z")  # Decision: 2026-02-01

    recs = [
        ForecastRecord(start_time=jan_1_delivery, publish_time=utc_dt("2025-12-31T09:00:00Z"), generation=10000.0),
        ForecastRecord(start_time=feb_2_delivery, publish_time=utc_dt("2026-02-01T09:00:00Z"), generation=11000.0),
    ]
    sel, _ = select_eligible_forecasts(recs, "2026-01-01", "2026-01-31", "09:50")
    assert len(sel) == 0


def test_hourly_actual_aggregation_requires_both_half_hours_and_averages_mw():
    """
    FUELHH 30-min generation must be averaged (not summed) and requires both
    half-hourly intervals (T:00 and T:30).
    """
    h0 = utc_dt("2026-01-02T12:00:00Z")
    h1 = utc_dt("2026-01-02T12:30:00Z")
    h2 = utc_dt("2026-01-02T13:00:00Z")  # 13:00 has no 13:30 pair

    half_hours = {
        h0: 10000.0,
        h1: 12000.0,
        h2: 15000.0,
    }

    hourly = aggregate_actuals_hourly(half_hours)

    # 12:00 hour is complete: average of 10000 and 12000 is 11000 MW (NOT 22000 MW sum!)
    assert hourly[h0] == 11000.0

    # 13:00 hour is incomplete (missing 13:30 reading): must be omitted
    assert h2 not in hourly


def test_duplicate_actual_revisions_resolved_deterministically():
    """When multiple FUELHH records exist for the same startTime, choose latest publishTime."""
    st = utc_dt("2026-01-02T12:00:00Z")
    recs = [
        ActualRecord(start_time=st, publish_time=utc_dt("2026-01-02T12:30:00Z"), generation=9000.0),
        ActualRecord(start_time=st, publish_time=utc_dt("2026-01-02T13:00:00Z"), generation=9500.0),  # Latest revision
        ActualRecord(start_time=st, publish_time=utc_dt("2026-01-02T12:45:00Z"), generation=9200.0),
    ]
    resolved = resolve_actual_records(recs)
    assert resolved[st] == 9500.0


def test_anti_leakage_proves_future_revision_cannot_influence_evaluation():
    """
    Crucial validation: Prove that a forecast revision published AFTER the cutoff
    cannot alter the selected forecast or corrupt the resulting accuracy metrics.
    """
    target = utc_dt("2026-01-02T10:00:00Z")
    # Decision: 2026-01-01, Cutoff: 09:50 UTC
    # Revision 1 (Eligible): published at 08:30 UTC -> 10,000 MW
    rev1 = ForecastRecord(start_time=target, publish_time=utc_dt("2026-01-01T08:30:00Z"), generation=10000.0)
    # Revision 2 (Leaked): published at 16:30 UTC -> 18,000 MW (heavily revised later)
    rev2 = ForecastRecord(start_time=target, publish_time=utc_dt("2026-01-01T16:30:00Z"), generation=18000.0)

    # Actual outturn for 10:00-11:00 is 10,200 MW
    hourly_actuals = {target: 10200.0}

    # Case A: Only eligible revision present
    sel_a, _ = select_eligible_forecasts([rev1], "2026-01-01", "2026-01-31", "09:50")
    aligned_a, _, _ = match_forecast_and_actuals(sel_a, hourly_actuals, "2026-01-01", "2026-01-31", "09:50")
    metrics_a = calculate_metrics(aligned_a)

    # Case B: Both eligible and leaked revision present in raw historical feed
    sel_b, excl_b = select_eligible_forecasts([rev1, rev2], "2026-01-01", "2026-01-31", "09:50")
    aligned_b, _, _ = match_forecast_and_actuals(sel_b, hourly_actuals, "2026-01-01", "2026-01-31", "09:50")
    metrics_b = calculate_metrics(aligned_b)

    # The selected forecast, observation, and accuracy metrics must be identical!
    assert excl_b == 1
    assert sel_a[target].generation == sel_b[target].generation == 10000.0
    assert metrics_a.mae == metrics_b.mae == 200.0
    assert metrics_a.mbe == metrics_b.mbe == -200.0
