import pytest


def test_get_summary_metrics_success(client):
    """Verify 200 OK, schema, exact hand-calculated metrics, and data quality counters."""
    response = client.get(
        "/api/summary-metrics",
        params={
            "decision_start_date": "2026-01-01",
            "decision_end_date": "2026-01-01",
            "cutoff_time": "09:50",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["filters"]["decision_start_date"] == "2026-01-01"
    assert data["filters"]["decision_end_date"] == "2026-01-01"
    assert data["filters"]["cutoff_time"] == "09:50"
    assert data["filters"]["delivery_start_date"] == "2026-01-02"
    assert data["filters"]["delivery_end_date"] == "2026-01-02"

    # Metrics evaluation
    metrics = data["metrics"]
    assert metrics["matched_count"] == 24
    assert metrics["mae"] == 200.0
    assert metrics["rmse"] == 200.0
    assert metrics["mbe"] == 200.0
    assert metrics["wape"] is not None

    # Data quality counters
    dq = data["data_quality"]
    assert dq["raw_fuelhh_count"] == 48
    assert dq["raw_windfor_count"] == 72
    assert dq["selected_forecast_count"] == 24
    assert dq["excluded_leakage_count"] == 24  # 24 post-cutoff revisions excluded
    assert dq["matched_count"] == 24
    assert dq["missing_actual_count"] == 0
    assert dq["missing_forecast_count"] == 0

    # Cache metadata
    meta = data["cache_metadata"]
    assert meta["cache_ttl_seconds"] > 0
    assert meta["data_retrieval_timestamp"] is not None


def test_get_summary_metrics_caching_on_repeat_call(client):
    """Second request with identical parameters must return cached result."""
    r1 = client.get(
        "/api/summary-metrics",
        params={"decision_start_date": "2026-01-01", "decision_end_date": "2026-01-01", "cutoff_time": "09:50"},
    )
    assert r1.status_code == 200

    r2 = client.get(
        "/api/summary-metrics",
        params={"decision_start_date": "2026-01-01", "decision_end_date": "2026-01-01", "cutoff_time": "09:50"},
    )
    assert r2.status_code == 200
    assert r2.json()["cache_metadata"]["cached"] is True


def test_get_summary_metrics_empty_matched_dataset(client):
    """When requested decision window has no available data, return null metrics and count 0."""
    # Mock data only covers decision date 2026-01-01 (delivery Jan 2)
    response = client.get(
        "/api/summary-metrics",
        params={
            "decision_start_date": "2026-01-10",
            "decision_end_date": "2026-01-15",
            "cutoff_time": "09:50",
        },
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]

    assert metrics["matched_count"] == 0
    assert metrics["mae"] is None
    assert metrics["rmse"] is None
    assert metrics["mbe"] is None
    assert metrics["wape"] is None
    assert data["data_quality"]["matched_count"] == 0
