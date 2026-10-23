from datetime import datetime, timezone
import pytest

from app.analysis_service import AnalysisService, RawDataCache
from app.models import ActualRecord, ForecastRecord


def test_raw_data_cache_lifecycle():
    """Verify cache store, TTL validity, and clear operations."""
    cache = RawDataCache(ttl_seconds=10)
    assert not cache.is_valid()
    assert cache.get() is None

    fuelhh = [ActualRecord(start_time=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), generation=100.0)]
    windfor = [ForecastRecord(start_time=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), publish_time=datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc), generation=120.0)]

    ts = cache.set(fuelhh, windfor)
    assert cache.is_valid()

    data = cache.get()
    assert data is not None
    assert len(data[0]) == 1
    assert len(data[1]) == 1
    assert data[2] == ts

    cache.clear()
    assert not cache.is_valid()
    assert cache.get() is None


def test_analysis_service_reuses_raw_data_for_different_cutoffs(test_service):
    """
    Changing cutoff or date filters must reuse cached raw datasets without making
    redundant upstream network calls.
    """
    # 1. First evaluation: fetches raw data (cache miss)
    summary1, _ = test_service.evaluate("2026-01-01", "2026-01-01", "09:50")
    assert not summary1.cache_metadata.cached

    # 2. Second evaluation with different cutoff: reuses raw cache (cache hit)
    summary2, _ = test_service.evaluate("2026-01-01", "2026-01-01", "05:00")
    assert summary2.cache_metadata.cached

    # Under 05:00 cutoff, the 08:30 revision is excluded, leaving the 04:30 revision!
    # Under 09:50 cutoff: selected forecast is 11200 MW (hour 0) vs actual 11000 MW -> error = +200 MW
    # Under 05:00 cutoff: selected forecast is 10500 MW (hour 0) vs actual 11000 MW -> error = -500 MW
    assert summary1.metrics.mae != summary2.metrics.mae
    assert summary1.metrics.mae == 200.0
    assert summary2.metrics.mae == 500.0


def test_analysis_service_close_is_safe(test_service):
    """Closing analysis service cleans up managed resources cleanly."""
    test_service.close()
    # Double close should not raise
    test_service.close()
