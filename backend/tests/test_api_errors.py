import httpx
import pytest
from fastapi.testclient import TestClient

from app.analysis_service import AnalysisService
from app.elexon_client import ElexonClient
from app.main import analysis_service, app


def test_invalid_date_formats_and_boundaries(client):
    """Ensure strict 400 Bad Request responses on invalid date formats and out-of-scope dates."""
    # 1. Invalid date string format
    r_bad_fmt = client.get("/api/summary-metrics", params={"decision_start_date": "01-01-2026"})
    assert r_bad_fmt.status_code == 400
    assert "Invalid date format" in r_bad_fmt.json()["detail"]

    # 2. Date before Jan 1, 2026
    r_early = client.get("/api/summary-metrics", params={"decision_start_date": "2025-12-31"})
    assert r_early.status_code == 400
    assert "must be within January 2026" in r_early.json()["detail"]

    # 3. Date after Jan 31, 2026
    r_late = client.get("/api/summary-metrics", params={"decision_end_date": "2026-02-01"})
    assert r_late.status_code == 400
    assert "must be within January 2026" in r_late.json()["detail"]

    # 4. Reversed date range (start > end)
    r_rev = client.get(
        "/api/summary-metrics",
        params={"decision_start_date": "2026-01-20", "decision_end_date": "2026-01-10"},
    )
    assert r_rev.status_code == 400
    assert "cannot be after" in r_rev.json()["detail"]


def test_invalid_cutoff_time_formats(client):
    """Ensure 400 Bad Request on invalid cutoff time strings."""
    for bad_cutoff in ["9:50", "25:00", "09:65", "abc", "09:50:00"]:
        r = client.get("/api/summary-metrics", params={"cutoff_time": bad_cutoff})
        assert r.status_code == 400
        assert "cutoff_time" in r.json()["detail"].lower()


def test_upstream_http_error_returns_502(monkeypatch):
    """When Elexon returns an HTTP error, the API returns 502 with clean JSON (no tracebacks)."""
    def error_handler(request: httpx.Request):
        return httpx.Response(500, text="Elexon Internal Server Error")

    transport = httpx.MockTransport(error_handler)
    mock_client = httpx.Client(transport=transport)
    bad_service = AnalysisService(
        elexon_client=ElexonClient(base_url="https://data.elexon.co.uk/bmrs/api/v1", client=mock_client),
    )

    analysis_service.client = bad_service.client
    analysis_service.clear_cache()

    with TestClient(app) as test_client:
        response = test_client.get("/api/summary-metrics")
        assert response.status_code == 502
        body = response.json()
        assert "upstream" in body["detail"].lower()
        # Ensure no traceback or internal path leakage
        assert "traceback" not in response.text.lower()
        assert "/Users/" not in response.text


def test_upstream_timeout_error_returns_502_or_504():
    """When Elexon connection times out, handle cleanly without unhandled crash."""
    def timeout_handler(request: httpx.Request):
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(timeout_handler)
    mock_client = httpx.Client(transport=transport)
    bad_service = AnalysisService(
        elexon_client=ElexonClient(base_url="https://data.elexon.co.uk/bmrs/api/v1", client=mock_client),
    )

    analysis_service.client = bad_service.client
    analysis_service.clear_cache()

    with TestClient(app) as test_client:
        response = test_client.get("/api/timeseries")
        assert response.status_code in (502, 504)
        assert "upstream" in response.json()["detail"].lower()
