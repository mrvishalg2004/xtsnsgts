from datetime import date, datetime, timedelta, timezone
import math
import threading
from typing import Dict, List, Optional, Tuple, Union
import httpx

from app.config import settings
from app.elexon_client import ElexonClient
from app.forecast_engine import (
    aggregate_actuals_hourly,
    get_decision_cutoff,
    get_query_boundaries,
    match_forecast_and_actuals,
    parse_date,
    resolve_actual_records,
    select_eligible_forecasts,
)
from app.metrics import calculate_metrics
from app.models import (
    ActualRecord,
    CacheMetadata,
    DataQualityCounts,
    EvaluationMetrics,
    FilterParameters,
    ForecastRecord,
    RevisionItem,
    RevisionsResponse,
    SummaryMetricsResponse,
    TimeseriesRecord,
    TimeseriesResponse,
    ensure_utc,
)


def ensure_finite(val: Optional[float]) -> Optional[float]:
    """Ensure float values are finite numbers, converting NaN or Infinity to None."""
    if val is None:
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return float(val)


class RawDataCache:
    """Thread-safe in-memory cache for raw retrieved Elexon datasets."""

    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self.fuelhh_records: Optional[List[ActualRecord]] = None
        self.windfor_records: Optional[List[ForecastRecord]] = None
        self.retrieval_timestamp: Optional[datetime] = None

    def is_valid(self) -> bool:
        with self._lock:
            if self.fuelhh_records is None or self.windfor_records is None or self.retrieval_timestamp is None:
                return False
            age = (datetime.now(timezone.utc) - self.retrieval_timestamp).total_seconds()
            return age < self.ttl_seconds

    def get(self) -> Optional[Tuple[List[ActualRecord], List[ForecastRecord], datetime]]:
        with self._lock:
            if not self.is_valid():
                return None
            return self.fuelhh_records, self.windfor_records, self.retrieval_timestamp  # type: ignore

    def set(self, fuelhh: List[ActualRecord], windfor: List[ForecastRecord]) -> datetime:
        with self._lock:
            now = datetime.now(timezone.utc)
            self.fuelhh_records = fuelhh
            self.windfor_records = windfor
            self.retrieval_timestamp = now
            return now

    def clear(self) -> None:
        with self._lock:
            self.fuelhh_records = None
            self.windfor_records = None
            self.retrieval_timestamp = None


class AnalysisService:
    """
    Orchestrates data ingestion, caching, leak-free forecast selection,
    and quantitative evaluation metrics.
    """

    def __init__(
        self,
        elexon_client: Optional[ElexonClient] = None,
        cache_ttl_seconds: Optional[int] = None,
    ):
        self.client = elexon_client or ElexonClient()
        self._owns_client = elexon_client is None
        ttl = cache_ttl_seconds or settings.CACHE_TTL_SECONDS
        self.cache = RawDataCache(ttl_seconds=ttl)
        self._analysis_lock = threading.RLock()
        # Computed analysis results cache: key -> (SummaryMetricsResponse, TimeseriesResponse, cached_at)
        self._computed_cache: Dict[str, Tuple[SummaryMetricsResponse, TimeseriesResponse, datetime]] = {}

    def close(self) -> None:
        """Close managed HTTP client resources cleanly."""
        if self._owns_client and hasattr(self.client, "_external_client") and self.client._external_client:
            self.client._external_client.close()

    def clear_cache(self) -> None:
        """Clear both raw data and computed analysis caches."""
        with self._analysis_lock:
            self.cache.clear()
            self._computed_cache.clear()

    def get_raw_data(self, force_refresh: bool = False) -> Tuple[List[ActualRecord], List[ForecastRecord], datetime, bool]:
        """
        Retrieve raw FUELHH and WINDFOR datasets. Reuses valid cached raw data
        or performs a fresh fetch if expired or force_refresh is True.
        """
        cached = self.cache.get()
        if cached is not None and not force_refresh:
            fuelhh, windfor, retrieval_ts = cached
            return fuelhh, windfor, retrieval_ts, True

        with self._analysis_lock:
            # Re-check inside lock
            cached = self.cache.get()
            if cached is not None and not force_refresh:
                fuelhh, windfor, retrieval_ts = cached
                return fuelhh, windfor, retrieval_ts, True

            # Query boundaries covering full January evaluation horizon plus December lookback
            bounds = get_query_boundaries(
                settings.DECISION_START_DATE,
                settings.DECISION_END_DATE,
                lookback_days=3,
            )

            # Ingest FUELHH actuals
            fuelhh_data = self.client.fetch_fuelhh(
                settlement_date_from=bounds["fuelhh_settlement_date_from"],
                settlement_date_to=bounds["fuelhh_settlement_date_to"],
                fuel_type="WIND",
            )

            # Ingest WINDFOR forecasts
            windfor_data = self.client.fetch_windfor(
                publish_date_time_from=bounds["windfor_publish_from"],
                publish_date_time_to=bounds["windfor_publish_to"],
            )

            # Store in thread-safe cache
            retrieval_ts = self.cache.set(fuelhh_data, windfor_data)
            self._computed_cache.clear()
            return fuelhh_data, windfor_data, retrieval_ts, False

    def _generate_expected_hourly_intervals(
        self,
        decision_start_d: date,
        decision_end_d: date,
    ) -> List[datetime]:
        """
        Generate all chronological hourly target intervals for the corresponding delivery dates.
        Delivery start: decision_start_d + 1 day at 00:00 UTC.
        Delivery end: decision_end_d + 1 day at 23:00 UTC.
        """
        deliv_start = decision_start_d + timedelta(days=1)
        deliv_end = decision_end_d + timedelta(days=1)

        start_dt = datetime(deliv_start.year, deliv_start.month, deliv_start.day, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(deliv_end.year, deliv_end.month, deliv_end.day, 23, 0, tzinfo=timezone.utc)

        intervals: List[datetime] = []
        cur = start_dt
        while cur <= end_dt:
            intervals.append(cur)
            cur += timedelta(hours=1)
        return intervals

    def evaluate(
        self,
        decision_start_date: str,
        decision_end_date: str,
        cutoff_time: str,
        force_refresh: bool = False,
    ) -> Tuple[SummaryMetricsResponse, TimeseriesResponse]:
        """
        Perform complete evaluation:
          1. Retrieve raw data (from cache or Elexon).
          2. Select eligible forecasts without lookahead leakage.
          3. Aggregate half-hourly actuals to hourly averages.
          4. Match observations and build complete expected delivery hour timeline.
          5. Calculate summary metrics.
        """
        cache_key = f"{decision_start_date}_{decision_end_date}_{cutoff_time}"

        with self._analysis_lock:
            if not force_refresh and cache_key in self._computed_cache:
                summary, timeseries, cached_at = self._computed_cache[cache_key]
                age = (datetime.now(timezone.utc) - cached_at).total_seconds()
                if age < self.cache.ttl_seconds:
                    cached_summary = summary.model_copy(
                        update={"cache_metadata": summary.cache_metadata.model_copy(update={"cached": True})}
                    )
                    cached_timeseries = timeseries.model_copy(
                        update={"cache_metadata": timeseries.cache_metadata.model_copy(update={"cached": True})}
                    )
                    return cached_summary, cached_timeseries

        fuelhh_raw, windfor_raw, retrieval_ts, was_cached = self.get_raw_data(force_refresh=force_refresh)

        start_d = parse_date(decision_start_date)
        end_d = parse_date(decision_end_date)
        deliv_start_d = start_d + timedelta(days=1)
        deliv_end_d = end_d + timedelta(days=1)

        # 1. Select eligible forecasts within the requested decision range and cutoff
        selected_forecasts, excluded_leakage_count = select_eligible_forecasts(
            windfor_raw,
            decision_start_date=decision_start_date,
            decision_end_date=decision_end_date,
            cutoff_time_str=cutoff_time,
        )

        # 2. Resolve duplicate/revised FUELHH actuals
        resolved_half_hours = resolve_actual_records(fuelhh_raw)

        # 3. Aggregate half-hourly actuals to complete hourly averages
        all_hourly_actuals = aggregate_actuals_hourly(resolved_half_hours)

        # Filter hourly actuals to the requested delivery range
        requested_hourly_actuals: Dict[datetime, float] = {}
        for dt, gen in all_hourly_actuals.items():
            deliv_d = dt.date()
            dec_d = deliv_d - timedelta(days=1)
            if start_d <= dec_d <= end_d:
                requested_hourly_actuals[dt] = gen

        # 4. Generate all expected hourly intervals across the delivery window
        expected_intervals = self._generate_expected_hourly_intervals(start_d, end_d)

        timeseries_records: List[TimeseriesRecord] = []
        matched_observations = []
        missing_actual_count = 0
        missing_forecast_count = 0
        missing_both_count = 0

        for target_dt in expected_intervals:
            deliv_d = target_dt.date()
            dec_d = deliv_d - timedelta(days=1)
            cutoff_dt = get_decision_cutoff(dec_d, cutoff_time)

            has_fc = target_dt in selected_forecasts
            has_act = target_dt in requested_hourly_actuals

            if has_fc and has_act:
                fc = selected_forecasts[target_dt]
                act_gen = requested_hourly_actuals[target_dt]
                err = ensure_finite(fc.generation - act_gen)
                abs_err = ensure_finite(abs(err)) if err is not None else None

                record = TimeseriesRecord(
                    target_start_time=target_dt,
                    delivery_date=deliv_d.isoformat(),
                    decision_date=dec_d.isoformat(),
                    decision_cutoff=cutoff_dt,
                    forecast_publish_time=fc.publish_time,
                    forecast_generation_mw=ensure_finite(fc.generation),
                    actual_generation_mw=ensure_finite(act_gen),
                    error_mw=err,
                    absolute_error_mw=abs_err,
                    availability_status="matched",
                )
                timeseries_records.append(record)

                # Collect for metrics calculation
                from app.models import AlignedObservation
                matched_observations.append(
                    AlignedObservation(
                        target_time=target_dt,
                        delivery_date=deliv_d.isoformat(),
                        decision_date=dec_d.isoformat(),
                        decision_cutoff=cutoff_dt,
                        forecast_generation=fc.generation,
                        actual_generation=act_gen,
                        forecast_publish_time=fc.publish_time,
                        error_mw=fc.generation - act_gen,
                        absolute_error_mw=abs(fc.generation - act_gen),
                    )
                )

            elif has_fc and not has_act:
                missing_actual_count += 1
                fc = selected_forecasts[target_dt]
                timeseries_records.append(
                    TimeseriesRecord(
                        target_start_time=target_dt,
                        delivery_date=deliv_d.isoformat(),
                        decision_date=dec_d.isoformat(),
                        decision_cutoff=cutoff_dt,
                        forecast_publish_time=fc.publish_time,
                        forecast_generation_mw=ensure_finite(fc.generation),
                        actual_generation_mw=None,
                        error_mw=None,
                        absolute_error_mw=None,
                        availability_status="missing_actual",
                    )
                )

            elif not has_fc and has_act:
                missing_forecast_count += 1
                act_gen = requested_hourly_actuals[target_dt]
                timeseries_records.append(
                    TimeseriesRecord(
                        target_start_time=target_dt,
                        delivery_date=deliv_d.isoformat(),
                        decision_date=dec_d.isoformat(),
                        decision_cutoff=cutoff_dt,
                        forecast_publish_time=None,
                        forecast_generation_mw=None,
                        actual_generation_mw=ensure_finite(act_gen),
                        error_mw=None,
                        absolute_error_mw=None,
                        availability_status="missing_forecast",
                    )
                )

            else:
                missing_both_count += 1
                timeseries_records.append(
                    TimeseriesRecord(
                        target_start_time=target_dt,
                        delivery_date=deliv_d.isoformat(),
                        decision_date=dec_d.isoformat(),
                        decision_cutoff=cutoff_dt,
                        forecast_publish_time=None,
                        forecast_generation_mw=None,
                        actual_generation_mw=None,
                        error_mw=None,
                        absolute_error_mw=None,
                        availability_status="missing_both",
                    )
                )

        # 5. Calculate statistical evaluation metrics
        metrics = calculate_metrics(
            matched_observations,
            missing_actual_count=missing_actual_count,
            missing_forecast_count=missing_forecast_count,
        )

        filter_params = FilterParameters(
            decision_start_date=decision_start_date,
            decision_end_date=decision_end_date,
            cutoff_time=cutoff_time,
            delivery_start_date=deliv_start_d.isoformat(),
            delivery_end_date=deliv_end_d.isoformat(),
        )

        data_quality = DataQualityCounts(
            raw_fuelhh_count=len(fuelhh_raw),
            raw_windfor_count=len(windfor_raw),
            selected_forecast_count=len(selected_forecasts),
            excluded_leakage_count=excluded_leakage_count,
            hourly_actual_count=len(requested_hourly_actuals),
            matched_count=len(matched_observations),
            missing_actual_count=missing_actual_count,
            missing_forecast_count=missing_forecast_count,
            missing_both_count=missing_both_count,
        )

        cache_meta = CacheMetadata(
            cached=was_cached,
            data_retrieval_timestamp=retrieval_ts,
            cache_ttl_seconds=self.cache.ttl_seconds,
        )

        summary_resp = SummaryMetricsResponse(
            status="ok",
            filters=filter_params,
            metrics=metrics,
            data_quality=data_quality,
            cache_metadata=cache_meta,
        )

        timeseries_resp = TimeseriesResponse(
            status="ok",
            filters=filter_params,
            total_periods=len(timeseries_records),
            records=timeseries_records,
            cache_metadata=cache_meta,
        )

        with self._analysis_lock:
            self._computed_cache[cache_key] = (summary_resp, timeseries_resp, datetime.now(timezone.utc))

        return summary_resp, timeseries_resp

    def get_revisions(
        self,
        target_start_time: datetime,
        cutoff_time: str = "09:50",
        force_refresh: bool = False,
    ) -> RevisionsResponse:
        """
        Inspect all historical forecast revisions published for a specific hourly target period.
        """
        fuelhh_raw, windfor_raw, retrieval_ts, was_cached = self.get_raw_data(force_refresh=force_refresh)

        target_utc = ensure_utc(target_start_time)
        deliv_d = target_utc.date()
        dec_d = deliv_d - timedelta(days=1)
        cutoff_dt = get_decision_cutoff(dec_d, cutoff_time)

        # Collect all revisions for this target period
        matching_recs = [r for r in windfor_raw if ensure_utc(r.start_time) == target_utc]
        # Sort chronologically by publishTime
        matching_recs.sort(key=lambda r: ensure_utc(r.publish_time))

        eligible = [r for r in matching_recs if ensure_utc(r.publish_time) <= cutoff_dt]
        selected_rec: Optional[ForecastRecord] = None
        if eligible:
            selected_rec = max(eligible, key=lambda r: ensure_utc(r.publish_time))

        items: List[RevisionItem] = []
        selected_item: Optional[RevisionItem] = None

        for r in matching_recs:
            is_elig = ensure_utc(r.publish_time) <= cutoff_dt
            is_sel = selected_rec is not None and r == selected_rec

            if is_sel:
                status_reason = "selected"
            elif is_elig:
                status_reason = "eligible_but_not_selected"
            else:
                status_reason = "published_after_cutoff"

            item = RevisionItem(
                publish_time=ensure_utc(r.publish_time),
                forecast_generation_mw=ensure_finite(r.generation) or 0.0,
                is_eligible=is_elig,
                is_selected=is_sel,
                status_reason=status_reason,
            )
            items.append(item)
            if is_sel:
                selected_item = item

        cache_meta = CacheMetadata(
            cached=was_cached,
            data_retrieval_timestamp=retrieval_ts,
            cache_ttl_seconds=self.cache.ttl_seconds,
        )

        return RevisionsResponse(
            status="ok",
            target_start_time=target_utc,
            delivery_date=deliv_d.isoformat(),
            decision_date=dec_d.isoformat(),
            decision_cutoff=cutoff_dt,
            total_revisions=len(items),
            eligible_revisions_count=len(eligible),
            selected_revision=selected_item,
            revisions=items,
            cache_metadata=cache_meta,
        )
