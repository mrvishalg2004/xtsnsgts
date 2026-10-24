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

### Analytical Finding on January 2, 2026 (MAE == MBE)
In real historical outturn on January 2, 2026, both MAE and MBE are exactly **3,196.21 MW**. Investigation confirms that across all 24 hours of that day, every single hourly forecast error was positive ($\text{forecast} \ge \text{actual}$, with forecast errors ranging from +2,868 MW to +3,500 MW). Because $e_t \ge 0$ for all $t$, $|e_t| = e_t$, meaning $\text{MAE} \equiv \text{MBE}$ identically. This is a mathematical property of uniform over-forecasting during that 24-hour delivery window.

---

## 4. Production REST API Endpoints

The FastAPI backend exposes the following REST endpoints on `http://localhost:8000`:

### A. Operational Health
* **`GET /api/health`**
* Returns JSON payload verifying service status and current UTC timestamp.

### B. Aggregated Summary Metrics
* **`GET /api/summary-metrics`**
* **Query Parameters:**
  * `decision_start_date` (string, default: `2026-01-01`): Must be within `2026-01-01` to `2026-01-31`.
  * `decision_end_date` (string, default: `2026-01-31`): Must be within `2026-01-01` to `2026-01-31`.
  * `cutoff_time` (string, default: `09:50`): Must be valid `HH:MM` in 24-hour UTC format.
* **Example Response:**
  ```json
  {
    "status": "ok",
    "filters": {
      "decision_start_date": "2026-01-01",
      "decision_end_date": "2026-01-01",
      "cutoff_time": "09:50",
      "delivery_start_date": "2026-01-02",
      "delivery_end_date": "2026-01-02"
    },
    "metrics": {
      "mae": 3196.21,
      "rmse": 3246.20,
      "mbe": 3196.21,
      "wape": 21.07,
      "matched_count": 24,
      "missing_actual_count": 0,
      "missing_forecast_count": 0
    },
    "data_quality": {
      "raw_fuelhh_count": 48,
      "raw_windfor_count": 949,
      "selected_forecast_count": 24,
      "excluded_leakage_count": 24,
      "hourly_actual_count": 24,
      "matched_count": 24,
      "missing_actual_count": 0,
      "missing_forecast_count": 0,
      "missing_both_count": 0
    },
    "cache_metadata": {
      "cached": false,
      "data_retrieval_timestamp": "2026-10-23T15:29:40.123456Z",
      "cache_ttl_seconds": 900
    }
  }
  ```

### C. Hourly Timeseries
* **`GET /api/timeseries`**
* **Query Parameters:** Same as summary endpoint (`decision_start_date`, `decision_end_date`, `cutoff_time`).
* **Response Structure:** Chronological ascending UTC array of all expected hourly delivery periods.
  ```json
  {
    "status": "ok",
    "filters": { ... },
    "total_periods": 24,
    "records": [
      {
        "target_start_time": "2026-01-02T00:00:00Z",
        "delivery_date": "2026-01-02",
        "decision_date": "2026-01-01",
        "decision_cutoff": "2026-01-01T09:50:00Z",
        "forecast_publish_time": "2026-01-01T08:30:00Z",
        "forecast_generation_mw": 18699.0,
        "actual_generation_mw": 15366.5,
        "error_mw": 3332.5,
        "absolute_error_mw": 3332.5,
        "availability_status": "matched"
      }
    ],
    "cache_metadata": { ... }
  }
  ```
* **Availability Statuses:** `matched`, `missing_forecast`, `missing_actual`, `missing_both`. Missing values are represented as `null`, never fabricated zeros.

### D. Revision Inspector
* **`GET /api/revisions`**
* **Query Parameters:**
  * `target_start_time` (string, required): Hourly ISO-8601 UTC timestamp (e.g. `2026-01-02T10:00:00Z`).
  * `cutoff_time` (string, default: `09:50`).
* **Response Structure:** Returns all available WINDFOR forecast publications for that target hour, classifying them as `selected`, `eligible_but_not_selected`, or `published_after_cutoff`.

---

### Caching & Resource Management
* **In-Memory TTL Cache:** Thread-safe caching with a default TTL of 15 minutes (`CACHE_TTL_SECONDS = 900`).
* **Filter Re-use:** When filters or cutoff times change, raw data is reused from the cache and analysis is recomputed in memory without redundant upstream network queries.
* **Instance Scope:** The in-memory cache is local to the backend instance.
* **Error Resilience:** Failed or partial requests are never cached as valid data. Upstream errors return HTTP 502/504 with sanitized JSON responses and no internal traceback leaks.

---

## 5. Interactive React Analytics Dashboard

The Phase 5 frontend transforms the application into an analytical trading-desk dashboard connected to the backend REST API:

### A. Dashboard Header & Temporal Distinction
* **Connectivity & Freshness:** Displays real backend operational status (`/api/health`) and real-time response cache metadata (`cache_metadata.cached` and retrieval timestamp).
* **Temporal Context:** Visibly contrasts the configured historical sample decision cutoff (default `09:50 UTC on D-1`) with the current live system clock, preventing confusion between historical evaluation benchmarks and real-time operations.

### B. Decision Parameters & Derived Delivery Window
* **Date Restrictions:** Filter inputs are strictly bounded to January 1–31, 2026 decision dates.
* **Derived Delivery Horizon:** Automatically displays the effective physical delivery window ($D+1$, January 2 – February 1, 2026).
* **Controlled Network Requests:** Inputs maintain a draft state so typing or changing dates does not trigger unconstrained network queries. Analysis is executed via an explicit **Apply Parameters** or **Run Analysis** action.
* **Transient Refresh Feedback:** If a manual refresh fails, previous successful results are retained while displaying a non-destructive banner indicating data age.

### C. Accuracy KPIs & Residual Metrics
* **Mean Absolute Error (MAE):** Average magnitude of hourly forecast deviations in MW.
* **Root Mean Squared Error (RMSE):** Variance-penalizing quadratic deviation in MW.
* **Mean Bias Error (MBE):** Directional signed deviation in MW ($F_t - A_t$). Visibly labeled with **Over-Forecast Bias** (amber), **Under-Forecast Bias** (blue/purple), or **Zero Bias** (green).
* **Weighted Absolute Percentage Error (WAPE):** Volume-weighted error percentage ($\sum |e_t| / \sum A_t \times 100\%$).
* **Matched Observations:** Statistical sample size of paired hours evaluated. Missing or unavailable metrics display as an em dash (`—`), never as zero.

### D. Generation & Error Visualizations
* **Forecast vs. Actual Time-Series Chart:** Two continuous series comparing the decision-time eligible wind forecast against actual outturn. Missing intervals preserve visual gaps (`connectNulls={false}`) without zero-imputation. Includes resolution view toggles (*Full Window*, *7 Days*, *24h Sample*) and hover tooltips showing publication timestamps.
* **Hourly Forecast Error Chart:** Plots signed residuals ($e_t = F_t - A_t$) against a visible zero reference line, color-coding over-forecast and under-forecast regimes without converting errors to absolute magnitudes.

### E. Data Quality & Reconciliation Audit
* Ingestion counters display raw FUELHH records, raw WINDFOR publications, selected pre-cutoff forecasts, post-cutoff leakage revisions excluded, complete hourly actuals, and paired observations.
* Confirms that missing observations are excluded from paired accuracy indicators without zero-imputation.

### F. Hourly Timeseries Ledger Table
* Chronological sortable table with delivery target times, delivery days, decision days, publication timestamps, forecast MW, actual MW, signed error MW, absolute error MW, and availability status badges (`Matched`, `Missing Forecast`, `Missing Actual`, `Missing Both`).
* Supports client-side sorting, status filtering, and multi-page pagination.

### G. Forecast Revision Inspector Modal
* Clicking **Inspect** on any delivery hour opens an audit drawer/modal querying `GET /api/revisions`.
* Displays the target delivery hour, decision cutoff, selected Day-Ahead benchmark, and the full chronological publication history of WINDFOR runs, categorizing each run as `selected`, `eligible_but_not_selected`, or `published_after_cutoff`.

---

## 6. Verification & Testing

### Running Full Backend Test Suite
All 45 unit and integration tests run offline without network dependencies:
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v
```

### Running Backend Tests Inside Docker
```bash
docker compose build backend
docker run --rm reintai-backend:latest pytest tests -v
```

### Running Frontend Tests
Frontend unit and integration tests (Vitest + React Testing Library + JSDOM):
```bash
npm --prefix frontend test
```

### Running Frontend Linting & Production Build
```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

### Bundle Size & Code Splitting Optimization
In Phase 6, the frontend bundle was optimized using Vite manual chunk splitting and dynamic component lazy-loading:
* **Vendor Chunk Separation:** Charting dependencies (`recharts`) are isolated into a dedicated `vendor-charts` chunk (`~403 KB`, `115 KB gzip`).
* **Dynamic Import:** The `RevisionInspector` audit modal is lazily imported on-demand via `React.lazy` and `Suspense` (`~6.2 KB`, `1.9 KB gzip`).
* **Core Application Bundle:** Main application JavaScript bundle was reduced from `662 KB` down to `254 KB` (`77 KB gzip`), completely eliminating Vite/Rollup bundle size warnings.

---

## 7. Cloud Production Deployment Architecture

The application is architected for zero-cost, resilient cloud deployment:
* **Frontend:** Deployed to **Vercel** as a static Vite Single Page Application (SPA).
* **Backend:** Deployed to **Render** as a Python Web Service.

```
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│     Vercel Production Edge      │           │     Render Cloud Web Service    │
│    (React 19 + Vite 8 SPA)      │  HTTPS    │        (FastAPI + Uvicorn)      │
│     https://<app>.vercel.app    │──────────>│   https://<api>.onrender.com    │
└─────────────────────────────────┘  REST     └─────────────────────────────────┘
                                                               │
                                                               │ HTTPS Stream
                                                               ▼
                                              ┌─────────────────────────────────┐
                                              │      Elexon Insights API        │
                                              │    (FUELHH & WINDFOR Datasets)  │
                                              └─────────────────────────────────┘
```

### Backend Deployment (Render Web Service)
* **Configuration:** Managed via root [`render.yaml`](file:///Users/abhijeetgolhar/Downloads/reintai/render.yaml) or interactive dashboard.
* **Root Directory:** `backend`
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* **Health Check Path:** `/api/health`
* **CORS Support:** Configured via `CORS_ORIGINS` and regex support for Vercel production and preview domains (`^https://.*\.vercel\.app$`).
* **Free Tier Considerations:** Render free web services spin down after 15 minutes of inactivity. Initial cold-start requests may take ~50 seconds to wake up; subsequent requests respond in milliseconds from memory cache.

### Frontend Deployment (Vercel)
* **Configuration:** Managed via [`frontend/vercel.json`](file:///Users/abhijeetgolhar/Downloads/reintai/frontend/vercel.json).
* **Framework Preset:** `Vite`
* **Root Directory:** `frontend`
* **Build Command:** `npm run build`
* **Output Directory:** `dist`
* **Install Command:** `npm ci`
* **Environment Variable:** `VITE_API_BASE_URL=https://<your-backend-host>`

### Local Multi-Container Deployment (Docker Compose)
To run the full stack locally in isolated Docker containers:
```bash
docker compose up -d
```
* **Interactive Dashboard:** `http://localhost:5173`
* **FastAPI Backend Root:** `http://localhost:8000`
* **API Documentation (Swagger UI):** `http://localhost:8000/docs`
* **Health Check Endpoint:** `http://localhost:8000/api/health`

---

## 8. Video Demonstration & Submission Documentation

* **10-Minute Video Demo Script:** Comprehensive scene-by-scene script and screen-recording plan for the required 10-minute unlisted YouTube presentation (Part 1 Client Pitch + Part 2 Technical Deep Dive) located in [`docs/demo-script.md`](file:///Users/abhijeetgolhar/Downloads/reintai/docs/demo-script.md).
* **Final Submission Checklist:** Step-by-step verification checklist for public URLs, Incognito testing, and form submission located in [`docs/submission-checklist.md`](file:///Users/abhijeetgolhar/Downloads/reintai/docs/submission-checklist.md).

---

## 9. Current Implementation Status

### Completed Implementation (Phases 1–6)
- [x] Initialized Git repository and confirmed remote compatibility.
- [x] Clean full-stack architecture (FastAPI backend + Vite React frontend).
- [x] Operational health endpoint (`GET /api/health`) and OpenAPI documentation (`/docs`).
- [x] Resilient Elexon HTTP client (`backend/app/elexon_client.py`) for `FUELHH` and `WINDFOR` streams.
- [x] Strict anti-leakage forecast revision selection engine (`backend/app/forecast_engine.py`).
- [x] Half-hourly to 1-hour actual aggregation and duplicate revision resolution.
- [x] Statistical accuracy metrics calculation (`backend/app/metrics.py`) with zero-denominator safety.
- [x] Reusable `AnalysisService` with thread-safe in-memory TTL caching.
- [x] Production REST API endpoints (`/api/summary-metrics`, `/api/timeseries`, `/api/revisions`).
- [x] Input validation and sanitized 400/502/504 error responses.
- [x] 45 comprehensive backend tests (unit, integration, error handling, caching, CORS, lifecycle, non-finite guards).
- [x] Interactive React dashboard with modular component architecture.
- [x] Decision parameters filter with draft state, Jan 2026 date bounds, and derived delivery range.
- [x] 5 summary KPI cards (MAE, RMSE, MBE with visual bias badges, WAPE, matched hours).
- [x] Forecast vs. actual generation time-series chart with gap preservation.
- [x] Signed forecast error residual chart with zero reference line and directional coloring.
- [x] Ingestion pipeline and data-quality audit panel with leakage-exclusion counters.
- [x] Chronological timeseries ledger table with sorting, pagination, and status badges.
- [x] Forecast revision inspector modal auditing WINDFOR publication runs.
- [x] Race-condition protection with request cancellation and stale response prevention.
- [x] Vitest and React Testing Library test suite (15 passing tests).
- [x] Docker Compose multi-container verification and live browser validation.
- [x] Production deployment configuration (`render.yaml`, `frontend/vercel.json`, CORS regex).
- [x] Bundle optimization and code splitting (main bundle reduced to 254 KB).
- [x] 10-minute client and technical YouTube demo script (`docs/demo-script.md`).
- [x] Final submission checklist and production acceptance verification (`docs/submission-checklist.md`).

---

## 10. AI Tool Disclosure

AI assistance: ChatGPT and Antigravity were used to assist with project planning, architectural design, implementation, and code review. All application logic, algorithms, tests, and user interfaces are verified through the documented test suites and browser validations.
