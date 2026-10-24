import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import httpx

from app.config import settings
from app.models import ActualRecord, ForecastRecord, ensure_utc


class ElexonAPIError(Exception):
    """Base exception for Elexon API integration errors."""
    pass


class ElexonHTTPError(ElexonAPIError):
    """Raised when an HTTP error status or network failure occurs."""
    pass


class ElexonDataValidationError(ElexonAPIError):
    """Raised when an unexpected response structure or invalid data is encountered."""
    pass


def parse_iso_utc(timestamp_str: Any) -> datetime:
    """Parse an ISO 8601 timestamp string into a timezone-aware UTC datetime."""
    if not isinstance(timestamp_str, str):
        raise ElexonDataValidationError(
            f"Expected timestamp string, got {type(timestamp_str).__name__}: {timestamp_str}"
        )
    try:
        # Standardize Z suffix for fromisoformat compatibility
        clean_str = timestamp_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            raise ElexonDataValidationError(
                f"Timestamp '{timestamp_str}' is timezone-naive. Timezone offset or 'Z' is required."
            )
        return dt.astimezone(timezone.utc)
    except Exception as e:
        raise ElexonDataValidationError(
            f"Failed to parse timestamp '{timestamp_str}': {e}"
        ) from e


def format_iso_utc(dt: Union[datetime, str]) -> str:
    """Format a datetime or string into standard UTC ISO 8601 string (e.g. 2026-01-01T00:00:00Z)."""
    if isinstance(dt, str):
        # Validate that it is parseable and convert to standardized Z string
        parsed = parse_iso_utc(dt)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(dt, datetime):
        utc_dt = ensure_utc(dt)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ElexonDataValidationError(f"Invalid datetime input: {dt}")


def normalize_fuelhh_record(raw: Dict[str, Any]) -> ActualRecord:
    """
    Validate and normalize a raw FUELHH record into an ActualRecord.
    Enforces fuelType == 'WIND' and finite numeric generation. Does not silently convert missing values to 0.
    """
    if not isinstance(raw, dict):
        raise ElexonDataValidationError(f"Expected dict record for FUELHH, got {type(raw).__name__}")

    fuel_type = raw.get("fuelType")
    if fuel_type != "WIND":
        raise ElexonDataValidationError(
            f"Invalid fuelType '{fuel_type}'. Expected 'WIND'."
        )

    start_time_raw = raw.get("startTime")
    if not start_time_raw:
        raise ElexonDataValidationError("FUELHH record missing required 'startTime' field")
    start_time = parse_iso_utc(start_time_raw)

    publish_time_raw = raw.get("publishTime")
    publish_time = parse_iso_utc(publish_time_raw) if publish_time_raw else None

    gen_raw = raw.get("generation")
    if gen_raw is None:
        raise ElexonDataValidationError(
            f"Missing required 'generation' field in FUELHH record for startTime={start_time_raw}"
        )
    try:
        generation = float(gen_raw)
    except (TypeError, ValueError) as e:
        raise ElexonDataValidationError(
            f"Invalid numeric generation '{gen_raw}' in FUELHH record: {e}"
        ) from e

    if not math.isfinite(generation):
        raise ElexonDataValidationError(
            f"Invalid non-finite generation value '{gen_raw}' in FUELHH record"
        )

    settlement_period = raw.get("settlementPeriod")
    if settlement_period is not None:
        try:
            settlement_period = int(settlement_period)
        except (ValueError, TypeError):
            settlement_period = None

    return ActualRecord(
        start_time=start_time,
        publish_time=publish_time,
        generation=generation,
        settlement_date=raw.get("settlementDate"),
        settlement_period=settlement_period,
        fuel_type="WIND",
    )


def normalize_windfor_record(raw: Dict[str, Any]) -> ForecastRecord:
    """
    Validate and normalize a raw WINDFOR record into a ForecastRecord.
    Validates required startTime, publishTime, and finite numeric generation.
    """
    if not isinstance(raw, dict):
        raise ElexonDataValidationError(f"Expected dict record for WINDFOR, got {type(raw).__name__}")

    start_time_raw = raw.get("startTime")
    publish_time_raw = raw.get("publishTime")

    if not start_time_raw:
        raise ElexonDataValidationError("WINDFOR record missing required 'startTime' field")
    if not publish_time_raw:
        raise ElexonDataValidationError("WINDFOR record missing required 'publishTime' field")

    start_time = parse_iso_utc(start_time_raw)
    publish_time = parse_iso_utc(publish_time_raw)

    gen_raw = raw.get("generation")
    if gen_raw is None:
        raise ElexonDataValidationError(
            f"Missing required 'generation' field in WINDFOR record for startTime={start_time_raw}"
        )
    try:
        generation = float(gen_raw)
    except (TypeError, ValueError) as e:
        raise ElexonDataValidationError(
            f"Invalid numeric generation '{gen_raw}' in WINDFOR record: {e}"
        ) from e

    if not math.isfinite(generation):
        raise ElexonDataValidationError(
            f"Invalid non-finite generation value '{gen_raw}' in WINDFOR record"
        )

    return ForecastRecord(
        start_time=start_time,
        publish_time=publish_time,
        generation=generation,
    )


class ElexonClient:
    """HTTP client for Elexon Insights Solution FUELHH and WINDFOR stream endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 25.0,
        client: Optional[httpx.Client] = None,
    ):
        self.base_url = (base_url or settings.ELEXON_BASE_URL).rstrip("/")
        self.timeout = timeout
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.Client(timeout=self.timeout)
            self._owns_client = True

    @property
    def is_closed(self) -> bool:
        """Check if internal client is closed."""
        return self._client.is_closed if self._client is not None else True

    def _get_client(self) -> httpx.Client:
        return self._client

    def close(self) -> None:
        """Close managed HTTP client if owned by this instance."""
        if self._owns_client and self._client is not None and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def fetch_fuelhh(
        self,
        settlement_date_from: str,
        settlement_date_to: str,
        fuel_type: str = "WIND",
        settlement_period: Optional[int] = None,
    ) -> List[ActualRecord]:
        """
        Fetch and normalize actual wind generation outturn from GET /datasets/FUELHH/stream.
        """
        endpoint = f"{self.base_url}/datasets/FUELHH/stream"
        params: Dict[str, Any] = {
            "settlementDateFrom": settlement_date_from,
            "settlementDateTo": settlement_date_to,
            "fuelType": fuel_type,
        }
        if settlement_period is not None:
            params["settlementPeriod"] = settlement_period

        records = self._request_json(endpoint, params=params)
        normalized: List[ActualRecord] = []
        for raw in records:
            # Defensively ensure only fuelType == "WIND" is included
            if raw.get("fuelType") == fuel_type:
                normalized.append(normalize_fuelhh_record(raw))

        return normalized

    def fetch_windfor(
        self,
        publish_date_time_from: Union[str, datetime],
        publish_date_time_to: Union[str, datetime],
    ) -> List[ForecastRecord]:
        """
        Fetch and normalize wind forecasts from GET /datasets/WINDFOR/stream.
        Query parameters require ISO UTC strings (publishDateTimeFrom / publishDateTimeTo).
        """
        endpoint = f"{self.base_url}/datasets/WINDFOR/stream"
        params: Dict[str, Any] = {
            "publishDateTimeFrom": format_iso_utc(publish_date_time_from),
            "publishDateTimeTo": format_iso_utc(publish_date_time_to),
        }

        records = self._request_json(endpoint, params=params)
        normalized: List[ForecastRecord] = []
        for raw in records:
            normalized.append(normalize_windfor_record(raw))

        return normalized

    def _request_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform HTTP GET request and parse JSON list response."""
        client = self._get_client()
        try:
            response = client.get(url, params=params)
        except httpx.RequestError as exc:
            raise ElexonHTTPError(f"HTTP request failed to {url}: {exc}") from exc

        if response.status_code != 200:
            raise ElexonHTTPError(
                f"Elexon API returned error status {response.status_code} for {url}. "
                f"Response body: {response.text[:200]}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise ElexonDataValidationError(
                f"Failed to parse JSON response from {url}: {exc}"
            ) from exc

        if not isinstance(data, list):
            raise ElexonDataValidationError(
                f"Expected JSON array from {url}, got {type(data).__name__}"
            )

        return data
