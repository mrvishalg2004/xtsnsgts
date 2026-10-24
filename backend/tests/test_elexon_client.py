import json
from datetime import datetime, timezone
import httpx
import pytest

from app.elexon_client import (
    ElexonClient,
    ElexonDataValidationError,
    ElexonHTTPError,
    format_iso_utc,
    normalize_fuelhh_record,
    normalize_windfor_record,
    parse_iso_utc,
)


def test_parse_iso_utc_and_format():
    """Verify UTC normalization and ISO formatting."""
    dt = parse_iso_utc("2026-01-01T04:30:00Z")
    assert dt.year == 2026
    assert dt.hour == 4
    assert dt.minute == 30
    assert dt.tzinfo == timezone.utc

    formatted = format_iso_utc(dt)
    assert formatted == "2026-01-01T04:30:00Z"

    with pytest.raises(ElexonDataValidationError):
        parse_iso_utc("invalid-timestamp")


def test_normalize_fuelhh_record_valid():
    """Verify normalization of a valid FUELHH wind record."""
    raw = {
        "dataset": "FUELHH",
        "publishTime": "2026-01-01T00:30:00Z",
        "startTime": "2026-01-01T00:00:00Z",
        "settlementDate": "2026-01-01",
        "settlementPeriod": 1,
        "fuelType": "WIND",
        "generation": 13756,
    }
    rec = normalize_fuelhh_record(raw)
    assert rec.fuel_type == "WIND"
    assert rec.generation == 13756.0
    assert rec.settlement_period == 1
    assert rec.start_time == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


def test_normalize_fuelhh_record_rejects_non_wind_and_invalid_generation():
    """Defensive validation: reject non-wind and missing/non-numeric generation."""
    # Non-wind
    with pytest.raises(ElexonDataValidationError, match="Invalid fuelType"):
        normalize_fuelhh_record({
            "startTime": "2026-01-01T00:00:00Z",
            "fuelType": "NUCLEAR",
            "generation": 5000,
        })

    # Missing generation: must not convert silently to 0
    with pytest.raises(ElexonDataValidationError, match="Missing required 'generation'"):
        normalize_fuelhh_record({
            "startTime": "2026-01-01T00:00:00Z",
            "fuelType": "WIND",
            "generation": None,
        })

    # Valid zero generation must be accepted
    zero_rec = normalize_fuelhh_record({
        "startTime": "2026-01-01T00:00:00Z",
        "fuelType": "WIND",
        "generation": 0,
    })
    assert zero_rec.generation == 0.0


def test_normalize_windfor_record_valid():
    """Verify normalization of a valid WINDFOR forecast record."""
    raw = {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-01T04:30:00Z",
        "startTime": "2026-01-01T05:00:00Z",
        "generation": 18250.5,
    }
    rec = normalize_windfor_record(raw)
    assert rec.generation == 18250.5
    assert rec.start_time == datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)
    assert rec.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)


def test_fetch_fuelhh_mocked_http_transport():
    """Verify endpoint URL, query parameters, and WIND response parsing using mock transport."""
    recorded_requests = []

    def mock_handler(request: httpx.Request):
        recorded_requests.append(request)
        assert request.url.path == "/bmrs/api/v1/datasets/FUELHH/stream"
        assert request.url.params["settlementDateFrom"] == "2026-01-01"
        assert request.url.params["settlementDateTo"] == "2026-01-02"
        assert request.url.params["fuelType"] == "WIND"

        payload = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 12500,
            },
            # Non-wind item should be filtered defensively
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "GAS",
                "generation": 8000,
            },
        ]
        return httpx.Response(200, json=payload)

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    elexon = ElexonClient(base_url="https://data.elexon.co.uk/bmrs/api/v1", client=mock_client)

    results = elexon.fetch_fuelhh("2026-01-01", "2026-01-02")
    assert len(results) == 1
    assert results[0].fuel_type == "WIND"
    assert results[0].generation == 12500.0


def test_fetch_windfor_mocked_http_transport():
    """Verify WINDFOR query parameters and response parsing."""
    def mock_handler(request: httpx.Request):
        assert request.url.path == "/bmrs/api/v1/datasets/WINDFOR/stream"
        assert request.url.params["publishDateTimeFrom"] == "2026-01-01T00:00:00Z"
        assert request.url.params["publishDateTimeTo"] == "2026-01-01T06:00:00Z"

        payload = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T04:30:00Z",
                "startTime": "2026-01-02T10:00:00Z",
                "generation": 16000,
            }
        ]
        return httpx.Response(200, json=payload)

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    elexon = ElexonClient(base_url="https://data.elexon.co.uk/bmrs/api/v1", client=mock_client)

    results = elexon.fetch_windfor("2026-01-01T00:00:00Z", "2026-01-01T06:00:00Z")
    assert len(results) == 1
    assert results[0].generation == 16000.0


def test_fetch_handles_empty_and_error_responses():
    """Verify empty response returns empty list and HTTP errors raise ElexonHTTPError."""
    # 1. Empty response
    def empty_handler(request: httpx.Request):
        return httpx.Response(200, json=[])

    client_empty = httpx.Client(transport=httpx.MockTransport(empty_handler))
    elexon_empty = ElexonClient(client=client_empty)
    assert elexon_empty.fetch_fuelhh("2026-01-01", "2026-01-01") == []

    # 2. HTTP 500 Server Error
    def error_handler(request: httpx.Request):
        return httpx.Response(500, text="Internal Server Error")

    client_error = httpx.Client(transport=httpx.MockTransport(error_handler))
    elexon_error = ElexonClient(client=client_error)
    with pytest.raises(ElexonHTTPError, match="500"):
        elexon_error.fetch_fuelhh("2026-01-01", "2026-01-01")


def test_elexon_client_owns_and_closes_internal_client():
    """Default ElexonClient instance owns its httpx.Client and closes it on close()."""
    client = ElexonClient()
    assert client._owns_client is True
    assert not client.is_closed
    client.close()
    assert client.is_closed is True


def test_elexon_client_preserves_injected_external_client():
    """ElexonClient does not close an externally injected httpx.Client."""
    external = httpx.Client()
    client = ElexonClient(client=external)
    assert client._owns_client is False
    client.close()
    assert not external.is_closed
    external.close()


def test_normalize_fuelhh_record_rejects_non_finite_values():
    """FUELHH record normalization rejects NaN and infinite generation values."""
    for val in [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity"]:
        with pytest.raises(ElexonDataValidationError, match="non-finite"):
            normalize_fuelhh_record({
                "startTime": "2026-01-01T00:00:00Z",
                "fuelType": "WIND",
                "generation": val,
            })


def test_normalize_windfor_record_rejects_non_finite_values():
    """WINDFOR record normalization rejects NaN and infinite generation values."""
    for val in [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity"]:
        with pytest.raises(ElexonDataValidationError, match="non-finite"):
            normalize_windfor_record({
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T20:00:00Z",
                "generation": val,
            })


def test_parse_iso_utc_rejects_timezone_naive():
    """parse_iso_utc strictly rejects timezone-naive ISO strings without UTC indicator."""
    with pytest.raises(ElexonDataValidationError, match="timezone-naive"):
        parse_iso_utc("2026-01-01T00:00:00")
