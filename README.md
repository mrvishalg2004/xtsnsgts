# Wind Forecast Insights

A small full-stack application for comparing UK wind-generation forecasts with actual generation. It was built as a day-ahead electricity market assessment project.

## Links

- **Web app:** https://xtsnsgts.vercel.app/
- **Backend API:** https://wind-forecast-insights-api.onrender.com
- **API health:** https://wind-forecast-insights-api.onrender.com/api/health
- **API docs:** https://wind-forecast-insights-api.onrender.com/docs
- **Source code:** https://github.com/mrvishalg2004/xtsnsgts

The backend runs on Render's free service. After a period without requests, it may take longer to respond while the service starts again.

## What the app does

A utility buying electricity a day ahead needs to estimate how much wind power will be available on the delivery day. A forecast published after the purchasing decision cannot be used to judge what the team knew at the time.

Wind Forecast Insights lets a user choose a decision-date range and a cutoff time, then compare the eligible forecast with the eventual wind-generation outturn. It shows summary error measures, an hourly comparison chart, signed forecast errors, data-quality counts, the underlying hourly records, and the publication history for a selected forecast.

This is an analysis and review tool. It does not buy electricity, forecast demand, estimate wholesale prices, or control power plants.

## Data used

The analysis uses only these two Elexon BMRS datasets:

- **Actual generation — FUELHH:** [API documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) · [API endpoint](https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream)
- **Wind forecast — WINDFOR:** [API documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) · [API endpoint](https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream)

FUELHH records are filtered to `fuelType = WIND`. The observed FUELHH records are half-hourly; WINDFOR target periods are hourly. The application uses `startTime` to identify the period being evaluated and `publishTime` to identify when a forecast was issued.

No API key is required for these public endpoints. The app does not call weather services or other market-data providers.

## Evaluation window and cutoff

The assessment asks for **purchasing decisions made in January 2026**, so the app uses these dates:

- **Decision dates:** 1–31 January 2026
- **Delivery dates:** 2 January–1 February 2026
- **Default sample cutoff:** 09:50 UTC on the decision date (D-1)

There are 744 expected hourly delivery periods in this window. The number used in the metrics can be lower if forecast or actual data are missing.

The 09:50 UTC cutoff is a configurable example based on the N2EX day-ahead timeline. It is not a universal cutoff for every UK electricity market. The selected cutoff is shown in the dashboard and can be changed in the filters.

## How the comparison works

For each hourly delivery period, the backend:

1. Finds the decision date (the calendar day before delivery) and calculates the cutoff datetime in UTC.
2. Keeps only WINDFOR revisions published at or before that cutoff (`publishTime <= decision_cutoff`).
3. If more than one revision is eligible for the same target hour, selects the one with the latest `publishTime`.
4. Uses the latest available FUELHH publication for a repeated actual target period, then averages the two half-hourly actual readings to match an hourly forecast.
5. Compares forecast and actual only when both are available.

The forecast is an hourly MW value, so the two half-hourly actual MW readings are averaged rather than added:

```text
hourly actual (MW) = (actual at HH:00 + actual at HH:30) / 2
```

If either half-hourly reading is missing, that hour is not treated as a complete actual. Missing values remain missing; they are not replaced with zero. Forecast revisions published after the decision cutoff are available in the revision inspector but are excluded from the day-ahead benchmark.

## Metrics

The signed error is defined as:

```text
error (MW) = forecast generation - actual generation
```

The dashboard reports:

- **MAE (MW):** average absolute error. It describes the typical size of the error without considering its direction.
- **RMSE (MW):** square-root of the mean squared error. Larger errors have more influence on this measure.
- **MBE (MW):** average signed error. A positive value means the forecast was higher than actual generation on average; a negative value means it was lower.
- **WAPE (%):** total absolute error divided by total absolute actual generation, multiplied by 100. It is shown as unavailable when the denominator is zero.
- **Matched hours:** number of forecast/actual pairs used in the metric calculations.

Missing forecast or actual periods are reported in the data-quality panel and are not included in paired metrics. Values shown in the interface are formatted for display; calculations use the underlying numeric values.

## Dashboard features

- Decision start date, end date, and UTC cutoff filters.
- KPI cards for MAE, RMSE, MBE, WAPE, and matched observations.
- Forecast-versus-actual hourly chart, with shorter time-window views.
- Signed forecast-error chart with a zero reference line.
- Data-quality counts for ingestion, eligible revisions, excluded post-cutoff revisions, and missing periods.
- Sortable and paginated hourly table.
- Forecast revision inspector showing which publication was selected and why later revisions were excluded.

## Run locally

### Option 1: Docker Compose

Install Docker Desktop, then run these commands from the repository root:

```bash
git clone https://github.com/mrvishalg2004/xtsnsgts.git
cd xtsnsgts
docker compose up --build
```

Open the app at [http://localhost:5173](http://localhost:5173). The FastAPI backend is available at [http://localhost:8000](http://localhost:8000), and its interactive API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

To stop the containers, run:

```bash
docker compose down
```

### Option 2: Run frontend and backend separately

Use Python 3.11 and Node.js 20 for a setup that matches the project's CI configuration.

**Backend** — in one terminal:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** — in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The frontend uses `http://localhost:8000` as its default API base URL for local development. To use a different backend, set `VITE_API_BASE_URL` in the frontend environment before running or building it.

## API endpoints

The analysis endpoints accept decision dates in January 2026 and a cutoff in `HH:MM` UTC format.

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Checks whether the backend is responding. |
| `GET /api/summary-metrics` | Returns the summary metrics, applied filters, data-quality counts, and cache metadata. |
| `GET /api/timeseries` | Returns hourly forecast, actual, error, and availability records in chronological order. |
| `GET /api/revisions` | Returns forecast revisions for a target hour and identifies the revision selected at the cutoff. |

Example full-window summary request:

```text
https://wind-forecast-insights-api.onrender.com/api/summary-metrics?decision_start_date=2026-01-01&decision_end_date=2026-01-31&cutoff_time=09:50
```

Example revision request:

```text
https://wind-forecast-insights-api.onrender.com/api/revisions?target_start_time=2026-01-02T00:00:00Z&cutoff_time=09:50
```

The backend validates date ranges and target timestamps. Upstream service failures return an error response rather than fabricated analysis results.

## Configuration

The main settings are listed in `.env.example`. Set them in the environment where the relevant service runs; do not commit a real `.env` file or secrets.

| Variable | Used by | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | Frontend | Base URL of the FastAPI service. |
| `CORS_ORIGINS` | Backend | Browser origins allowed to call the API. |
| `ELEXON_BASE_URL` | Backend | Base URL for the Elexon BMRS API. |
| `DEFAULT_DECISION_CUTOFF_TIME` | Backend | Default decision cutoff, in UTC. |
| `CACHE_TTL_SECONDS` | Backend | Lifetime of cached source data; defaults to 900 seconds. |

The cache is in memory and belongs to one backend instance. It is not shared between multiple instances. A cache hit means the app reused recently fetched data; it does not mean the data is being continuously refreshed.

## Tests and checks

Run backend tests from the `backend` directory after installing its requirements:

```bash
pytest tests -v
```

Run frontend tests, linting, and a production build from the `frontend` directory:

```bash
npm ci
npm test
npm run lint
npm run build
```

The backend tests use deterministic fixtures and mocked HTTP responses so the standard test suite does not depend on Elexon's availability. Live API checks are separate from the automated tests.

The GitHub Actions workflow runs the backend tests and frontend checks on the repository.

## Repository layout

```text
.
├── .github/workflows/ci.yml       # Automated checks
├── backend/
│   ├── app/
│   │   ├── analysis_service.py    # Coordinates fetching, caching, and analysis
│   │   ├── config.py              # Application settings
│   │   ├── elexon_client.py       # Elexon API client
│   │   ├── forecast_engine.py     # Cutoff selection and time alignment
│   │   ├── main.py                # FastAPI app and routes
│   │   ├── metrics.py             # Accuracy calculations
│   │   └── models.py              # Data and response models
│   ├── tests/                     # Backend unit and API tests
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/            # Dashboard, charts, table, revision inspector
│   │   ├── services/api.js        # Backend requests
│   │   ├── utils/formatters.js    # Display formatting
│   │   ├── __tests__/             # Frontend tests
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── vercel.json
│   └── Dockerfile
├── docs/
│   ├── demo-script.md             # Script for the required video
│   └── submission-checklist.md    # Submission and access checks
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── render.yaml
└── README.md
```

## Deployment

The frontend is hosted on Vercel and the API on Render. The Render Blueprint configuration is in `render.yaml`; the Vite deployment configuration is in `frontend/vercel.json`.

For Vercel, use `frontend` as the project root and set `VITE_API_BASE_URL` to:

```text
https://wind-forecast-insights-api.onrender.com
```

For Render, use the root-level Blueprint to configure the backend service. The current service is configured to use `/api/health` as its health check.

The free Render service can spin down when idle, so the first request after a quiet period may be slower. If the public app shows a connection error, check the Render service status and logs before changing application code.

## Known limits

- The application analyses wind generation only. It does not use demand forecasts, generation plant schedules, wholesale prices, or other fuels.
- The 09:50 UTC cutoff is an example assumption. Confirm the applicable cutoff with the actual trading venue before using this approach for operational decisions.
- Forecast accuracy metrics describe the selected historical window; they do not guarantee future forecast performance or financial savings.
- The in-memory cache is temporary and instance-local.
- The required unlisted YouTube demo and assessment-form submission must be completed separately from deploying the code.

