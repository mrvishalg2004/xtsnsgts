# Wind Forecast Insights — Final Submission Checklist

> **Assessment Title:** Full Stack SWE Challenge Submission v4  
> **Repository:** `https://github.com/mrvishalg2004/xtsnsgts.git`  
> **Evaluation Window:** UK Wind Generation Day-Ahead Forecasts (January 1–31, 2026 decisions / January 2–February 1, 2026 delivery)

---

## 1. Submission Deliverables Summary

| Deliverable | Target / Platform | Production Status | Verified Public URL |
| :--- | :--- | :--- | :--- |
| **Source Code Repository** | GitHub | **Ready & Pushed** | `https://github.com/mrvishalg2004/xtsnsgts` |
| **Frontend Dashboard** | Vercel (Vite React SPA) | **Deployment Configured** | *Pending user Vercel link* (see deployment steps below) |
| **Backend REST API** | Render (FastAPI Web Service) | **Deployment Configured** | *Pending user Render link* (see deployment steps below) |
| **Backend Health Probe** | Render Web Service | **Deployment Configured** | `https://<backend-host>/api/health` |
| **Interactive API Docs** | FastAPI Swagger UI | **Deployment Configured** | `https://<backend-host>/docs` |
| **10-Minute Video Demo** | YouTube (Unlisted) | **Script Ready in docs/** | *Pending user screen recording & upload* (see [demo-script.md](file:///Users/abhijeetgolhar/Downloads/reintai/docs/demo-script.md)) |
| **Official Submission Form** | "Full Stack SWE challenge submission v4" | **Ready for entry** | Complete form in your browser |

---

## 2. Deployment Instructions for Hosting Platforms

### Step A: Deploy Backend to Render (Free Web Service)
1. Log in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New + > Web Service**.
3. Connect the GitHub repository: `mrvishalg2004/xtsnsgts`.
4. Configure service settings:
   - **Name:** `wind-forecast-insights-api`
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Region:** Frankfurt (EU Central) or London (nearest to UK Elexon API)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** `Free`
5. Under **Advanced > Health Check Path**, enter: `/api/health`.
6. Add Environment Variables:
   - `ENVIRONMENT` = `production`
   - `CORS_ORIGINS` = `https://<your-vercel-app>.vercel.app,http://localhost:5173`
   - `ELEXON_BASE_URL` = `https://data.elexon.co.uk/bmrs/api/v1`
   - `DEFAULT_DECISION_CUTOFF_TIME` = `09:50`
   - `DECISION_START_DATE` = `2026-01-01`
   - `DECISION_END_DATE` = `2026-01-31`
   - `DELIVERY_START_DATE` = `2026-01-02`
   - `DELIVERY_END_DATE` = `2026-02-01`
   - `CACHE_TTL_SECONDS` = `900`
7. Click **Create Web Service**.
8. Once deployed, note your public URL (e.g. `https://wind-forecast-insights-api.onrender.com`).
9. Verify health endpoint: `https://<backend-host>/api/health` -> should return `{"status":"ok"}`.

### Step B: Deploy Frontend to Vercel (Free Vite Preset)
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New... > Project**.
3. Import the GitHub repository: `mrvishalg2004/xtsnsgts`.
4. In Project Settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** click Edit and select `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm ci`
5. In **Environment Variables**, add:
   - `VITE_API_BASE_URL` = `https://<your-backend-host>` (use the real Render URL from Step A)
6. Click **Deploy**.
7. Once deployed, test the public URL (e.g. `https://xtsnsgts.vercel.app`).

---

## 3. Pre-Submission Verification Checklist

Run these manual acceptance checks before submitting the final form:

- [ ] **Incognito Browser Verification (Frontend):**
  - Open a clean Incognito/Private window.
  - Navigate to the public Vercel frontend URL.
  - Confirm the page loads instantly without requiring any login or credentials.
  - Verify the header displays **Backend Connected** with green status.
  - Confirm the default decision range shows `2026-01-01` to `2026-01-31` with cutoff `09:50 UTC`.
  - Confirm the derived delivery window displays `2026-01-02` to `2026-02-01`.
  - Confirm all 5 KPI cards populate with live data (MAE, RMSE, MBE with bias badge, WAPE, 744 matched hours).
  - Confirm the generation chart and signed error chart render clearly without errors.
  - Scroll down to the timeseries ledger, click **Inspect** on a row, and verify that the revision modal opens with historical WINDFOR publications.
  - Open browser DevTools (F12) > Console: confirm 0 errors.

- [ ] **Incognito Browser Verification (Backend API):**
  - In the incognito window, open `https://<backend-host>/api/health`. Confirm JSON response with status `"ok"`.
  - Open `https://<backend-host>/docs`. Confirm FastAPI Swagger UI loads with documentation for all endpoints.

- [ ] **Incognito Browser Verification (YouTube Demo Video):**
  - Record and upload the 10-minute demo following [docs/demo-script.md](file:///Users/abhijeetgolhar/Downloads/reintai/docs/demo-script.md).
  - Open the YouTube link in an Incognito window without signing in.
  - Confirm the video is set to **Unlisted** (not Private).
  - Confirm audio is clear and total duration is under 10:00 minutes.

---

## 4. Final Submission Form Steps

1. Open the form titled: **"Full Stack SWE challenge submission v4 – Fill out form"**.
2. Enter your verified public links:
   - **GitHub Repository URL:** `https://github.com/mrvishalg2004/xtsnsgts`
   - **Live Deployed Application URL:** `https://<your-vercel-app>.vercel.app`
   - **Unlisted Video Demo URL:** `https://youtu.be/<your-video-id>`
   - **API Documentation URL (if requested):** `https://<backend-host>/docs`
3. Confirm all links are accessible without authentication.
4. Submit the form and retain the confirmation confirmation/email.
