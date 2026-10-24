# Wind Forecast Insights — 10-Minute Video Demo Script & Recording Plan

> **Format:** 1 Video | **Target Runtime:** 8:45 – 9:30 min (Strict Max: 10:00 min)  
> **Structure:** Part 1 (Client Presentation, ~4:15 min) + Part 2 (Technical Walkthrough, ~4:30 min)  
> **Audience:** Wholesale Power Trading & Portfolio Dispatch Teams (Part 1) + Senior Quantitative Software Engineers (Part 2)

---

## Recording & Production Guidelines

### Screen Capture Setup
1. **Resolution:** 1920×1080 (1080p, 16:9) at 30fps or 60fps.
2. **Audio:** Clear desktop or lapel microphone; minimize background noise.
3. **Browser Setup:** Chrome / Edge full-screen window (100% zoom). Close unrelated tabs and disable OS notifications.
4. **Target URL:** Deployed production URL or local production build on `http://localhost:5173`. Ensure backend (`http://localhost:8000`) is running.

---

## PART 1: Client & Commercial Presentation (0:00 – 4:15)

*Target Length: 4 minutes 15 seconds (Max: 5:00 min)*  
*Focus: Business problem, day-ahead auction dynamics, KPI interpretation, and trading decision support.*

### Scene 1.1: The Wholesale Power Purchasing Problem (0:00 – 0:45)
- **On-Screen Action:** Display the dashboard top view showing header, brand, and temporal bar. Cursor hovers over "Configured Sample Decision Cutoff: 09:50 UTC".
- **Spoken Script:**
  > "Hello. When commercial power trading and portfolio dispatch teams participate in the UK Day-Ahead electricity auction—such as the N2EX auction—they face a fundamental risk: contracting wholesale power commitments based on variable wind generation.
  >
  > In wholesale power markets, contracts cleared on Day $D-1$ dictate physical delivery throughout Day $D$. The trading desk must submit binding volume bids prior to auction gate closure—modeled in our application at a sample cutoff of 09:50 UTC on Day $D-1$.
  >
  > If the desk relies on an inaccurate wind generation forecast, they face expensive cash-out imbalance penalties or must buy replacement power in volatile intraday markets.
  >
  > The purpose of **Wind Forecast Insights** is straightforward: to quantitatively evaluate the exact wind generation forecasts that were available to traders at the decision cutoff, comparing them against subsequent physical outturn without future-data lookahead bias."

### Scene 1.2: Decision Windows & Scope Parameters (0:45 – 1:30)
- **On-Screen Action:** Scroll gently to the **Trading Decision Parameters** panel. Highlight the date inputs: `2026-01-01` to `2026-01-31`. Point out the derived effective physical delivery window: `2026-01-02` to `2026-02-01`.
- **Spoken Script:**
  > "Let's examine the decision parameters. The evaluation window covers contracting decisions made from January 1st to January 31st, 2026.
  >
  > Crucially, our platform enforces the physical separation between decision dates and delivery dates. A decision made on January 1st contracts power delivered on January 2nd ($D+1$). The entire month's decisions evaluate 744 hourly delivery periods ending February 1st.
  >
  > Notice the sample decision cutoff: 09:50 UTC. This is a documented N2EX auction timeline assumption. The dashboard allows configurable cutoffs because different UK wholesale venues, such as EPEX SPOT, clear at different cutoff times.
  >
  > When filters are adjusted, the platform maintains draft state and only executes analysis upon explicit user action, preventing unnecessary network flooding."

### Scene 1.3: Statistical Accuracy KPIs (1:30 – 2:30)
- **On-Screen Action:** Move down to the **Key Forecast Accuracy Indicators** grid. Hover over MAE, RMSE, MBE, WAPE, and Matched Hours.
- **Spoken Script:**
  > "Across the full January 2026 decision window, the platform evaluates 744 matched hourly delivery periods.
  >
  > First, **Mean Absolute Error (MAE)** stands at 2,013.0 MW. This represents the average magnitude of hourly deviation between day-ahead forecasts and actual delivery.
  >
  > Second, **Root Mean Squared Error (RMSE)** is 2,505.9 MW. Because RMSE squares deviations before averaging, it heavily penalizes large forecast misses—vital for dispatchers managing reserve capacity.
  >
  > Third, **Mean Bias Error (MBE)** shows a positive bias of +1,729.9 MW, flagged here with an amber 'Over-Forecast Bias' badge. On average, the day-ahead forecast systematically overstated actual wind production by over 1.7 GW. For a trading desk, persistent over-forecasting means contracting for power you don't actually generate, forcing costly balance settlement purchases.
  >
  > Fourth, **Weighted Absolute Percentage Error (WAPE)** is 17.84%. Unlike simple MAPE, which distorts accuracy during low-wind periods due to small denominators, WAPE divides total absolute error by total actual generation, providing a reliable volume-weighted benchmark."

### Scene 1.4: Time-Series Visualizations & Gap Preservation (2:30 – 3:15)
- **On-Screen Action:** Scroll to the **Day-Ahead Wind Forecast vs. Actual Generation** chart. Toggle the view from 'Full Window' to 'First 7 Days', then hover over individual data points to trigger custom tooltips.
- **Spoken Script:**
  > "Here in the time-series chart, the cyan line depicts the day-ahead available forecast, while the green line represents verified actual generation.
  >
  > When hovering over any hour, the tooltip reveals the exact forecast publication timestamp, delivery hour, and signed deviation.
  >
  > Notice an important data integrity rule: if a forecast or actual measurement is missing, the chart preserves visual gaps (`connectNulls=false`). It never imputes missing data as zero megawatts. Treating missing data as zero would completely distort statistical accuracy.
  >
  > Below, the **Hourly Forecast Error Chart** plots signed residuals with an explicit zero reference line. Amber bars indicate over-forecasting, while purple bars highlight under-forecasting periods."

### Scene 1.5: Forecast Revision Audit & Client Takeaways (3:15 – 4:15)
- **On-Screen Action:** Scroll down to the **Hourly Timeseries Ledger**. Click the **Inspect** button on row `2026-01-02 00:00 UTC` to open the **Forecast Revision History** modal. Highlight the 'Selected Benchmark' and the 'Excluded (Post-Cutoff)' rows.
- **Spoken Script:**
  > "A common commercial dispute in post-trade analysis is: *'Which forecast was actually available when we traded?'*
  >
  > Clicking 'Inspect' opens our Forecast Revision Inspector. Here, for delivery on January 2nd at midnight, Elexon published multiple revisions across December 31st and January 1st. The system correctly identifies the 09:30 UTC publication on January 1st at 18,699 MW as the official selected benchmark—the latest revision prior to the 09:50 UTC cutoff.
  >
  > Later runs, such as the 11:30 UTC publication at 18,800 MW, are explicitly flagged as 'Excluded (Post-Cutoff)'. Even though they predicted January 2nd delivery, they were published after the day-ahead auction closed. Including them would introduce lookahead bias.
  >
  > In summary, this pilot proves that trading teams can systematically quantify wind forecast exposure, audit revision eligibility, and eliminate lookahead bias from their trading performance attribution. It does not execute trades or guarantee savings; it provides the reliable quantitative foundation for commercial decision-making."

---

## PART 2: Technical Architecture & Implementation Review (4:15 – 8:45)

*Target Length: 4 minutes 30 seconds (Max: 5:00 min)*  
*Focus: Full-stack architecture, Elexon ingestion pipeline, anti-leakage engine, caching, tests, and deployment.*

### Scene 2.1: Full-Stack Architecture & Official Datasets (4:15 – 5:00)
- **On-Screen Action:** Switch briefly to VS Code or architecture diagram. Show project tree: `backend/` (FastAPI) and `frontend/` (React + Vite). Open `backend/app/elexon_client.py`.
- **Spoken Script:**
  > "Turning to the technical implementation: the application is built as a clean, decoupled full-stack platform using Python with FastAPI for the analytical backend, and React 19 with Vite for the frontend dashboard.
  >
  > The system ingests two official Elexon Insights Solution streams:
  > 1. The `FUELHH` stream for half-hourly physical actual generation, filtered defensively to `fuelType = WIND`.
  > 2. The `WINDFOR` stream for hourly wind forecast publications across rolling 72-hour horizons.
  >
  > No secondary weather APIs, simulated distributions, or external price feeds are used. The data pipeline is strictly grounded in official UK transmission system operator records."

### Scene 2.2: Temporal Alignment & Anti-Leakage Selection Engine (5:00 – 6:00)
- **On-Screen Action:** Open `backend/app/forecast_engine.py`. Highlight `select_eligible_forecasts()` and `aggregate_actuals_hourly()`.
- **Spoken Script:**
  > "The core algorithmic challenge lies in temporal resolution and leakage prevention.
  >
  > First, temporal alignment: Elexon WINDFOR forecasts are published hourly, whereas FUELHH actuals are published half-hourly (settlement periods 1 to 48).
  > To match them legitimately, our engine constructs complete hourly actuals by averaging both half-hourly settlement periods: $(SP_t + SP_{t+30}) / 2.0$. Because MW is an instantaneous power rate, generation values must be averaged, never summed. If either half-hour is missing, the hour is marked incomplete and excluded from paired evaluation.
  >
  > Second, the strict anti-leakage rule: for any target hour on delivery day $D$, the decision cutoff timestamp $T_{\text{cutoff}}$ is established at $D-1$ at the specified cutoff time (09:50 UTC).
  > The selector filters all available forecast records to `publishTime <= T_cutoff` and selects the latest eligible revision ($\max(\text{publishTime})$). Revisions published after cutoff are strictly quarantined."

### Scene 2.3: REST API Architecture & Thread-Safe Caching (6:00 – 6:45)
- **On-Screen Action:** Open `backend/app/main.py` and `backend/app/analysis_service.py`. Point to the routes: `/api/summary-metrics`, `/api/timeseries`, and `/api/revisions`.
- **Spoken Script:**
  > "The analysis service exposes three core REST endpoints:
  > - `/api/summary-metrics`: computes MAE, RMSE, MBE, WAPE, and comprehensive data quality counters.
  > - `/api/timeseries`: produces chronological hourly ledger records with availability statuses (`matched`, `missing_forecast`, `missing_actual`, `missing_both`).
  > - `/api/revisions`: provides the full publication run audit trail for any delivery period.
  >
  > To deliver low-latency responses, `AnalysisService` incorporates a thread-safe in-memory cache protected by re-entrant locks (`threading.RLock`).
  > Raw Elexon records are cached with a 15-minute TTL. When a user modifies decision parameters or cutoff times, the service recomputes metrics instantaneously from cached source data without redundant upstream API downloads."

### Scene 2.4: Frontend Engineering & Code-Splitting (6:45 – 7:30)
- **On-Screen Action:** Open `frontend/src/App.jsx` and `frontend/vite.config.js`. Show `AbortController` request cancellation and manual rollup chunks.
- **Spoken Script:**
  > "On the frontend, the React application is refactored into focused, reusable components.
  >
  > Key frontend engineering highlights include:
  > - **Race-Condition Protection:** API fetches use `AbortController` and incremental request IDs. When a user applies new filter parameters, in-flight requests are automatically aborted so obsolete network responses can never overwrite newer state.
  > - **Bundle Optimization:** In Phase 6, we implemented code-splitting. Heavy chart visualization libraries are isolated into a dedicated `vendor-charts` chunk, and the `RevisionInspector` modal is lazily loaded via `React.lazy` and `Suspense`. This reduced the main JavaScript bundle from 662 KB down to 254 KB (77 KB gzipped)—eliminating bundler size warnings.
  > - **Error Resilience:** Failed refreshes preserve prior successful state while displaying non-destructive warnings."

### Scene 2.5: Test Suite, Docker, & Deployment Verification (7:30 – 8:45)
- **On-Screen Action:** Open terminal. Run backend tests: `pytest`. Run frontend tests: `npm test`. Show Docker Compose file.
- **Spoken Script:**
  > "Production readiness is backed by thorough test suites:
  > - The backend pytest suite contains 36 automated unit and integration tests covering math precision, anti-leakage selection, caching concurrency, 400 parameter validation, and 502 upstream error handling.
  > - The frontend test suite contains 15 Vitest and React Testing Library tests verifying KPI rendering, em-dash null display, table sorting, modal behavior, and stale request cancellation.
  >
  > The full system is containerized via Docker Compose with dedicated backend and frontend services.
  >
  > For public cloud deployment, the FastAPI service is packaged for Render using its `/api/health` probe and dynamic PORT binding, while the React Vite SPA is deployed to Vercel with clean client-side routing rewrites.
  >
  > All code has been developed with disciplined Git commits, complete documentation, and zero fabricated metrics. Thank you."

---

## Post-Recording & YouTube Upload Checklist

1. **Review Recorded Runtime:** Confirm total recording time is between **8:00 and 9:45 minutes** (Strict maximum: 10:00 min).
2. **Export Video:** Export MP4 at 1080p H.264 with AAC audio.
3. **Upload to YouTube:**
   - Go to [YouTube Studio](https://studio.youtube.com).
   - Click **Create > Upload Videos**.
   - Title: `Wind Forecast Insights — UK Electricity Market Forecast Analytics Demo`
   - Description: Include link to GitHub repository (`https://github.com/mrvishalg2004/xtsnsgts`) and brief summary.
   - Visibility: Select **Unlisted** (anyone with the link can view; not public or private).
4. **Verification:**
   - Copy the YouTube video link.
   - Open a clean/incognito browser window without signing into Google.
   - Confirm video plays smoothly with audio and 1080p resolution.
5. **Update Checklist:** Insert the verified YouTube URL into `docs/submission-checklist.md` and `README.md`.
