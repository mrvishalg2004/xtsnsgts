from datetime import datetime, timezone
import httpx
import pytest
from fastapi.testclient import TestClient

from app.analysis_service import AnalysisService
from app.elexon_client import ElexonClient
from app.main import analysis_service as global_analysis_service, app


@pytest.fixture
def mock_fuelhh_data():
    """Synthetic FUELHH half-hourly wind actuals for Jan 2, 2026."""
    records = []
    # 24 hours on 2026-01-02 = 48 settlement periods
    # SP1: 00:00 (10000 MW), SP2: 00:30 (12000 MW) -> Hourly average = 11000 MW
    for sp in range(1, 49):
        hour = (sp - 1) // 2
        minute = 30 if sp % 2 == 0 else 0
        st = f"2026-01-02T{hour:02d}:{minute:02d}:00Z"
        # Deterministic generation formula: 10000 + hour * 100 + minute * 10
        gen = 10000.0 + hour * 100.0 + (2000.0 if minute == 30 else 0.0)
        records.append({
            "dataset": "FUELHH",
            "publishTime": f"2026-01-02T{hour:02d}:45:00Z",
            "startTime": st,
            "settlementDate": "2026-01-02",
            "settlementPeriod": sp,
            "fuelType": "WIND",
            "generation": gen,
        })
    return records


@pytest.fixture
def mock_windfor_data():
    """
    Synthetic WINDFOR forecast records with multiple revisions:
    - Pre-cutoff revision (published 2026-01-01T04:30:00Z)
    - Cutoff-eligible revision (published 2026-01-01T08:30:00Z)
    - Exact cutoff revision (published 2026-01-01T09:50:00Z)
    - Post-cutoff leaked revision (published 2026-01-01T14:30:00Z)
    """
    records = []
    for hour in range(0, 24):
        st = f"2026-01-02T{hour:02d}:00:00Z"
        # 1. Early eligible run
        records.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T04:30:00Z",
            "startTime": st,
            "generation": 10500.0 + hour * 100.0,
        })
        # 2. Latest eligible run before 09:50 (e.g. at 08:30 UTC)
        records.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T08:30:00Z",
            "startTime": st,
            "generation": 11200.0 + hour * 100.0,  # Expected selected forecast
        })
        # 3. Post-cutoff revision at 14:30 UTC (must be excluded)
        records.append({
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T14:30:00Z",
            "startTime": st,
            "generation": 25000.0 + hour * 100.0,  # Distorted future revision
        })
    return records


@pytest.fixture
def mock_elexon_client(mock_fuelhh_data, mock_windfor_data):
    """ElexonClient backed by httpx.MockTransport serving deterministic synthetic fixtures."""
    def handler(request: httpx.Request):
        url_path = request.url.path
        if "FUELHH/stream" in url_path:
            return httpx.Response(200, json=mock_fuelhh_data)
        elif "WINDFOR/stream" in url_path:
            return httpx.Response(200, json=mock_windfor_data)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return ElexonClient(base_url="https://data.elexon.co.uk/bmrs/api/v1", client=http_client)


@pytest.fixture
def test_service(mock_elexon_client):
    """AnalysisService configured with mock client and isolated cache."""
    service = AnalysisService(elexon_client=mock_elexon_client, cache_ttl_seconds=300)
    service.clear_cache()
    return service


@pytest.fixture
def client(test_service):
    """FastAPI TestClient with injected test_service."""
    global_analysis_service.client = test_service.client
    global_analysis_service.clear_cache()
    with TestClient(app) as test_client:
        yield test_client
    global_analysis_service.clear_cache()
