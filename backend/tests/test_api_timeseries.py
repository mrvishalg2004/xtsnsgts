from datetime import datetime, timezone
import pytest


def test_get_timeseries_chronological_ordering_and_fields(client):
    """Verify chronological UTC sorting, delivery date translation, and metric signs."""
    response = client.get(
        "/api/timeseries",
        params={
            "decision_start_date": "2026-01-01",
            "decision_end_date": "2026-01-01",
            "cutoff_time": "09:50",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["total_periods"] == 24
    records = data["records"]
    assert len(records) == 24

    # Verify chronological ascending order
    prev_dt = datetime.min.replace(tzinfo=timezone.utc)
    for rec in records:
        target_dt = datetime.fromisoformat(rec["target_start_time"].replace("Z", "+00:00"))
        assert target_dt > prev_dt
        prev_dt = target_dt

        # Delivery date mapping
        assert rec["delivery_date"] == "2026-01-02"
        assert rec["decision_date"] == "2026-01-01"
        assert rec["availability_status"] == "matched"

        # Math verification: error_mw = forecast - actual
        fc = rec["forecast_generation_mw"]
        act = rec["actual_generation_mw"]
        err = rec["error_mw"]
        abs_err = rec["absolute_error_mw"]

        assert fc is not None and act is not None
        assert round(fc - act, 2) == round(err, 2)
        assert abs_err == abs(err)


def test_timeseries_handles_missing_observations_transparently(client):
    """Periods with missing forecasts or actuals return null fields and clear status."""
    # Requesting dates where mock data does not have observations
    response = client.get(
        "/api/timeseries",
        params={
            "decision_start_date": "2026-01-10",
            "decision_end_date": "2026-01-10",
            "cutoff_time": "09:50",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_periods"] == 24  # 24 delivery hours on 2026-01-11

    for rec in data["records"]:
        assert rec["availability_status"] == "missing_both"
        assert rec["forecast_generation_mw"] is None
        assert rec["actual_generation_mw"] is None
        assert rec["error_mw"] is None
        assert rec["absolute_error_mw"] is None
        assert rec["forecast_publish_time"] is None
