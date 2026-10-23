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
1. **Actual Generation:** [`FUELHH` stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
   * Half-hourly generation outturn filtered to `fuelType = WIND`.
   * Key fields: `startTime`, `generation`, `fuelType`, `settlementDate`, `settlementPeriod`.
2. **Forecast Generation:** [`WINDFOR` stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
   * System-wide wind generation forecasts published in rolling multi-day runs (~73 hourly horizon intervals per run).
   * Key fields: `startTime`, `publishTime`, `generation`.

*Note: No external weather services, secondary market APIs, or credentials are required or permitted.*

---

## 2. Key Analytical & Market Cutoff Assumptions

### January 2026 Decision-Date Interpretation
In the UK wholesale electricity market, day-ahead auction contracts for delivery day $D$ (settlement periods across 00:00 to 24:00 UTC) are cleared on day $D-1$.
* A purchasing decision made on **January 1, 2026** contracts power for delivery on **January 2, 2026**.
* A purchasing decision made on **January 31, 2026** contracts power for delivery on **February 1, 2026**.
* For deliveries occurring on January 1, 2026, the corresponding decision occurred on December 31, 2025.

### Sample Decision Cutoff Assumption (09:50 UTC)
* The default sample cutoff configured in this application is **09:50 UTC on Day $D-1$**.
* **Important Market Distinction:** This is a configurable sample cutoff modeled on the N2EX UK Day-Ahead auction timeline. It is **not** a universal market cutoff across all UK power exchanges (for example, EPEX SPOT and bilateral trade notifications may use different auction cutoffs such as 09:20, 11:00, or 12:00 UTC).
* The cutoff time is fully configurable in environment settings and application parameters.

### Anti-Leakage Rule (Preventing Lookahead Bias)
For any delivery period $t$ on day $D$, the forecast selection engine strictly selects the latest forecast publication where:
$$\text{publishTime} \le T_{\text{cutoff}} \quad (\text{on Day } D-1)$$
Revisions published after this cutoff—even if published prior to physical gate closure or delivery—are excluded from the day-ahead decision benchmark.

---

## 3. Project Directory Structure

```
reintai/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (backend tests & frontend build)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application, CORS, and health endpoints
│   │   └── config.py            # Environment-driven configuration & market assumptions
│   ├── tests/
│   │   └── test_health.py       # Automated health check and routing tests
│   ├── requirements.txt         # Backend Python dependencies
│   └── Dockerfile               # Multi-stage Python 3.11 container definition
├── frontend/
│   ├── src/
│   │   ├── services/
│   │   │   └── api.js           # Configurable API client
│   │   ├── App.jsx              # Application shell & real-time health indicator
│   │   ├── main.jsx             # React entrypoint
│   │   └── index.css            # High-contrast trading-desk styling
│   ├── package.json             # Frontend dependencies (React 19, Vite)
│   ├── package-lock.json        # Deterministic dependency lockfile
│   ├── index.html               # Semantic HTML5 entrypoint
│   ├── vite.config.js           # Vite dev server configuration
│   └── Dockerfile               # Node.js 20 container definition
├── .env.example                 # Example configuration file
├── .gitignore                   # Excludes venvs, node_modules, build outputs, secrets
├── docker-compose.yml           # Multi-service local development orchestration
└── README.md                    # Project documentation
```

---

## 4. Current Implementation Status

### Implemented in Phase 2
- [x] Initialized Git repository and confirmed remote compatibility.
- [x] Clean minimal project architecture (FastAPI backend + Vite React frontend).
- [x] FastAPI operational health endpoint (`GET /api/health`) and OpenAPI interactive documentation (`/docs`).
- [x] Environment-driven CORS middleware enabling local Vite frontend access.
- [x] React shell displaying product purpose, scope parameters, and live backend connection status.
- [x] Containerization with `Dockerfile`s and `docker-compose.yml` exposing ports 5173 and 8000.
- [x] Automated test suite verifying backend health response (`pytest`).
- [x] GitHub Actions CI workflow executing backend tests and frontend build on push.

### Remaining for Future Phases
- [ ] Phase 3: Elexon API data ingestion (FUELHH stream & WINDFOR stream), half-hour to 1-hour temporal aggregation, cutoff-based leak-free forecast revision engine, and quantitative metric calculations (MAE, RMSE, WAPE, Mean Bias Error).
- [ ] Phase 4: Production REST API endpoints with caching for fast interactive filtering.
- [ ] Phase 5: Interactive trading-desk frontend dashboard with time-series charts, cutoff selector, and error distribution.
- [ ] Phase 6: Production deployment configuration and end-to-end verification.

*Note: No fabricated or mock metrics are shown on the UI in this phase.*

---

## 5. Local Setup & Development Instructions

### Prerequisites
* **Python:** 3.11+
* **Node.js:** 20+ and npm
* **Docker & Docker Compose** (optional for containerized run)

### Running with Docker Compose (Recommended)
To build and start both the frontend and backend services:

```bash
docker compose up --build
```

Access points:
* **Frontend Application:** [http://localhost:5173](http://localhost:5173)
* **Backend API Health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
* **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the containers:
```bash
docker compose down
```

---

### Running Manually

#### Backend Setup
```bash
# 1. Create and activate a Python virtual environment
cd backend
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run automated tests
pytest tests -v

# 4. Start the backend development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
# 1. Install dependencies from lockfile
cd frontend
npm ci

# 2. Verify production build
npm run build

# 3. Start the frontend development server
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) in your browser.

---

## 6. Verification & Automated Testing

### Backend Unit Tests
Execute the test suite from the repository root:
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v
```

Expected result:
```
backend/tests/test_health.py::test_health_check_returns_ok PASSED
backend/tests/test_health.py::test_root_endpoint_returns_info PASSED
```

### Frontend Build Verification
```bash
npm --prefix frontend run build
```

---

## 7. AI Tool Disclosure

AI assistance: ChatGPT and Antigravity were used to assist with project planning, implementation, and code review. Application behavior is validated through the documented tests and verification steps.
