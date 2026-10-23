# Wind Forecast Insights

> UK Day-Ahead Electricity Market Wind-Generation Forecast Evaluation Platform

## 1. Product Purpose & Scope

**Wind Forecast Insights** is a production-grade analytical web platform designed for electricity trading, dispatch, and portfolio management teams.

The product solves a critical decision-support problem in wholesale power markets:
* **Pre-contract evaluation:** Understanding the wind-generation forecasts actually available at the precise moment day-ahead purchasing decisions are executed.
* **Accuracy verification:** Quantitatively evaluating forecast accuracy against subsequent actual physical outturn without future-data leakage (lookahead bias).

### Target Evaluation Window
* **Decision Dates:** January 1, 2026 – January 31, 2026
* **Delivery Dates:** January 2, 2026 – February 1, 2026 (day-ahead physical delivery $D+1$)

### Official Elexon Data Sources In Scope
Only official Elexon Insights Solution datasets are used:
1. **Actual Wind Generation:** [`FUELHH` stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
   * Base URL: `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
   * Granularity: Half-hourly outturn by fuel type (48 settlement periods per standard day, spaced by 30 minutes: `:00` and `:30`).
   * Filtered to `fuelType = WIND`.
   * Key fields: `startTime`, `generation` (MW), `fuelType`, `settlementDate`, `settlementPeriod`, `publishTime`.
2. **Forecast Wind Generation:** [`WINDFOR` stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
   * Base URL: `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
   * Granularity: Strictly hourly target intervals (`startTime` increments in 1-hour steps: `:00`).
   * Cadence & Horizon: Forecast runs published every 2 to 4 hours, each containing ~73 hourly horizon intervals (~3 days ahead).
   * Key fields: `startTime`, `publishTime`, `generation` (MW).

*Note: No external weather services, secondary market APIs, or credentials are required or permitted.*

---

## 2. Methodology & Analytical Principles

### January 2026 Decision-Date vs Delivery-Date
In the UK wholesale electricity market, day-ahead auction contracts for delivery day $D$ (settlement periods across 00:00 to 24:00 UTC) are cleared on day $D-1$.
* A purchasing decision made on **January 1, 2026** contracts power for delivery on **January 2, 2026**.
* A purchasing decision made on **January 31, 2026** contracts power for delivery on **February 1, 2026**.
* Decisions outside January 1–31, 2026 are excluded from the January analysis.

### Sample Decision Cutoff Assumption (09:50 UTC)
* The default sample cutoff configured in this application is **09:50 UTC on Day $D-1$**.
* **Market Context:** This is a configurable sample cutoff modeled on the N2EX UK Day-Ahead auction timeline. It is **not** a universal market cutoff across all UK power exchanges (for example, EPEX SPOT and bilateral trade notifications may use different auction cutoffs such as 09:20, 11:00, or 12:00 UTC).
* The cutoff time is fully configurable in environment settings and application parameters.

### Anti-Leakage Rule (Preventing Lookahead Bias)
For each target delivery period $t$ on day $D$:
1. The decision date is $D - 1$.
2. The cutoff datetime is calculated as `datetime(D-1 at cutoff_time UTC)`.
3. Only forecast records with $\text{publishTime} \le T_{\text{cutoff}}$ are eligible.
4. If multiple eligible forecast revisions exist for target period $t$, the engine selects the latest eligible revision ($\max(\text{publishTime})$).
5. All revisions published after $T_{\text{cutoff}}$—including revisions published later on Day $D-1$ or during delivery Day $D$—are strictly excluded from the evaluation benchmark.

### December Horizon Lookback
Because WINDFOR publishes rolling 72-hour forecast horizons, forecasts published on December 30–31, 2025 were available before the January 1, 2026 cutoff to forecast January 2, 2026 deliveries. The ingestion query bounds include a safety lookback of 3 days prior to January 1 to guarantee full coverage without data gaps.

### Temporal Alignment & Actual Data Handling
* **Hourly Aggregation:** Because WINDFOR has hourly resolution and FUELHH has half-hourly resolution, each delivery hour $T$ requires both distinct half-hourly settlement periods ($T:00$ and $T:30$).
* **Averaging Rule:** Hourly actual generation is computed as the arithmetic mean:
  $$\text{actual\_generation} = \frac{\text{gen}(T:00) + \text{gen}(T:30)}{2.0} \quad [\text{MW}]$$
  *(Generation values are in MW, representing instantaneous power rates; they must never be summed).*
* **Incomplete Hours:** If either half-hourly period is missing, the hour is marked incomplete and excluded from paired evaluation rather than fabricating an observation from a single 30-minute reading.
* **Actual Revision Selection:** If multiple FUELHH publications exist for the same half-hourly `startTime`, the revision with the latest `publishTime` is selected deterministically.

---

## 3. Quantitative Accuracy Metrics

Evaluation is performed exclusively on matched pairs of day-ahead forecasts and complete actual outturn:

$$\text{error\_mw} = \text{forecast\_generation} - \text{actual\_generation}$$

1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |\text{forecast}_t - \text{actual}_t| \quad [\text{MW}]$$
2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N (\text{forecast}_t - \text{actual}_t)^2} \quad [\text{MW}]$$
3. **Mean Bias Error (MBE):**
   $$\text{MBE} = \frac{1}{N} \sum_{t=1}^N (\text{forecast}_t - \text{actual}_t) \quad [\text{MW}]$$
   *Positive bias indicates systematic over-forecasting; negative bias indicates under-forecasting.*
4. **Weighted Absolute Percentage Error (WAPE):**
   $$\text{WAPE} = \frac{\sum_{t=1}^N |\text{forecast}_t - \text{actual}_t|}{\sum_{t=1}^N |\text{actual}_t|} \times 100\% \quad [\%]$$
   *When $\sum |\text{actual}_t| = 0$, WAPE returns `None` (null) to prevent division by zero.*
5. **Observation Counts:**
   * `matched_count`: Number of valid hourly pairs evaluated.
   * `missing_actual_count`: Delivery hours with eligible forecasts but incomplete actuals.
   * `missing_forecast_count`: Delivery hours with complete actuals but no forecast before cutoff.

*Note: MAPE is omitted as a primary metric because near-zero actual generation causes division-by-zero or distorted percentage values.*

---

## 4. Current Implementation Status

### Implemented in Phase 2 & Phase 3
- [x] Initialized Git repository and confirmed remote compatibility.
- [x] Clean minimal project architecture (FastAPI backend + Vite React frontend).
- [x] FastAPI operational health endpoint (`GET /api/health`) and OpenAPI interactive documentation (`/docs`).
- [x] Resilient Elexon HTTP client (`backend/app/elexon_client.py`) for `FUELHH` and `WINDFOR` streams with defensive validation.
- [x] Strict anti-leakage forecast revision selection engine (`backend/app/forecast_engine.py`).
- [x] Half-hourly to 1-hour actual aggregation and duplicate revision resolution.
- [x] Statistical accuracy metrics calculation (`backend/app/metrics.py`) with zero-denominator safety.
- [x] Domain models for normalized records, observations, and evaluation metrics (`backend/app/models.py`).
- [x] Complete automated unit test suite with 21 passing offline tests (`pytest`).
- [x] Bounded live API smoke test verifying Elexon stream schemas and January 2026 data outturn.
- [x] Containerization with `Dockerfile`s and `docker-compose.yml`.

### Remaining for Future Phases
- [ ] Phase 4: Production REST API endpoints (`/api/forecasts`, `/api/actuals`, `/api/metrics`, `/api/compare`) with caching.
- [ ] Phase 5: Interactive trading-desk frontend dashboard with time-series charts, cutoff selector, and error distribution.
- [ ] Phase 6: Production deployment configuration and end-to-end verification.

---

## 5. Verification & Testing

### Running Backend Unit Tests Locally
All unit tests execute offline without requiring live network connectivity:
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v
```

### Running Backend Unit Tests Inside Docker
```bash
docker compose build backend
docker run --rm reintai-backend:latest pytest tests -v
```

Expected result:
```
tests/test_elexon_client.py::test_parse_iso_utc_and_format PASSED
tests/test_elexon_client.py::test_normalize_fuelhh_record_valid PASSED
tests/test_elexon_client.py::test_normalize_fuelhh_record_rejects_non_wind_and_invalid_generation PASSED
tests/test_elexon_client.py::test_normalize_windfor_record_valid PASSED
tests/test_elexon_client.py::test_fetch_fuelhh_mocked_http_transport PASSED
tests/test_elexon_client.py::test_fetch_windfor_mocked_http_transport PASSED
tests/test_elexon_client.py::test_fetch_handles_empty_and_error_responses PASSED
tests/test_forecast_engine.py::test_decision_cutoff_derivation PASSED
tests/test_forecast_engine.py::test_query_boundaries_include_december_lookback PASSED
tests/test_forecast_engine.py::test_december_publication_eligible_for_early_january_delivery PASSED
tests/test_forecast_engine.py::test_forecast_cutoff_boundary_inclusion_and_exclusion PASSED
tests/test_forecast_engine.py::test_out_of_scope_dates_are_excluded PASSED
tests/test_forecast_engine.py::test_hourly_actual_aggregation_requires_both_half_hours_and_averages_mw PASSED
tests/test_forecast_engine.py::test_duplicate_actual_revisions_resolved_deterministically PASSED
tests/test_forecast_engine.py::test_anti_leakage_proves_future_revision_cannot_influence_evaluation PASSED
tests/test_health.py::test_health_check_returns_ok PASSED
tests/test_health.py::test_root_endpoint_returns_info PASSED
tests/test_metrics.py::test_hand_calculated_metrics_precision PASSED
tests/test_metrics.py::test_negative_bias PASSED
tests/test_metrics.py::test_zero_actual_generation_preserves_validity_and_handles_wape PASSED
tests/test_metrics.py::test_empty_observations PASSED
======================== 21 passed in 0.24s =========================
```

### Frontend Build Verification
```bash
npm --prefix frontend run build
```

---

## 6. AI Tool Disclosure

AI assistance: ChatGPT and Antigravity were used to assist with project planning, implementation, and code review. Application behavior is validated through the documented tests and verification steps.
