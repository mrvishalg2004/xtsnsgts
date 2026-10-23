import { useState, useEffect } from 'react';
import { checkHealth, API_BASE_URL } from './services/api';

export default function App() {
  const [healthStatus, setHealthStatus] = useState('loading'); // 'loading' | 'available' | 'unavailable'
  const [healthData, setHealthData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchHealth = async () => {
    setHealthStatus('loading');
    setErrorMessage(null);
    try {
      const data = await checkHealth();
      setHealthData(data);
      setHealthStatus('available');
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      setHealthStatus('unavailable');
      setErrorMessage(err.message || 'Unable to communicate with the backend service');
      setLastChecked(new Date().toLocaleTimeString());
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <div className="brand-logo">
            <span className="logo-icon">⚡</span>
            <div>
              <h1 className="brand-title">Wind Forecast Insights</h1>
              <p className="brand-subtitle">UK Day-Ahead Electricity Market Analytics</p>
            </div>
          </div>
        </div>
        <div className="header-right">
          <div className={`status-pill status-${healthStatus}`}>
            <span className="status-dot"></span>
            <span className="status-label">
              {healthStatus === 'loading' && 'Checking Backend...'}
              {healthStatus === 'available' && 'Backend Connected'}
              {healthStatus === 'unavailable' && 'Backend Offline'}
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="overview-card">
          <div className="section-header">
            <h2>Product Purpose & Scope</h2>
            <span className="badge badge-primary">Elexon BMRS In Scope</span>
          </div>
          <p className="overview-text">
            This application enables electricity trading and dispatch teams to quantitatively evaluate
            the accuracy of wind-generation forecasts available at the exact moment UK day-ahead purchasing
            decisions are contracted.
          </p>

          <div className="scope-grid">
            <div className="scope-item">
              <span className="scope-label">Decision Window:</span>
              <span className="scope-value">January 1 – January 31, 2026</span>
            </div>
            <div className="scope-item">
              <span className="scope-label">Delivery Window:</span>
              <span className="scope-value">January 2 – February 1, 2026</span>
            </div>
            <div className="scope-item">
              <span className="scope-label">Sample Decision Cutoff:</span>
              <span className="scope-value">09:50 UTC (Configurable N2EX sample)</span>
            </div>
            <div className="scope-item">
              <span className="scope-label">Actual Data Stream:</span>
              <span className="scope-value">Elexon FUELHH (WIND)</span>
            </div>
            <div className="scope-item">
              <span className="scope-label">Forecast Data Stream:</span>
              <span className="scope-value">Elexon WINDFOR</span>
            </div>
            <div className="scope-item">
              <span className="scope-label">Anti-Leakage Rule:</span>
              <span className="scope-value">Strict (publishTime ≤ cutoff on D-1)</span>
            </div>
          </div>
        </section>

        <section className="health-card">
          <div className="section-header">
            <h2>Backend Service Health</h2>
            <button className="btn-secondary" onClick={fetchHealth} disabled={healthStatus === 'loading'}>
              {healthStatus === 'loading' ? 'Verifying...' : 'Re-check Connection'}
            </button>
          </div>

          <div className="health-body">
            <div className="health-row">
              <span className="health-key">Configured API Base URL:</span>
              <code className="code-tag">{API_BASE_URL}</code>
            </div>
            <div className="health-row">
              <span className="health-key">Health Endpoint:</span>
              <code className="code-tag">{API_BASE_URL}/api/health</code>
            </div>
            <div className="health-row">
              <span className="health-key">Service Status:</span>
              <span className={`health-badge badge-${healthStatus}`}>
                {healthStatus.toUpperCase()}
              </span>
            </div>

            {healthData && (
              <div className="health-details">
                <div className="detail-item">
                  <span className="detail-label">Service:</span>
                  <span className="detail-value">{healthData.service || 'N/A'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Version:</span>
                  <span className="detail-value">{healthData.version || 'N/A'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Environment:</span>
                  <span className="detail-value">{healthData.environment || 'development'}</span>
                </div>
                {lastChecked && (
                  <div className="detail-item">
                    <span className="detail-label">Last Checked:</span>
                    <span className="detail-value">{lastChecked}</span>
                  </div>
                )}
              </div>
            )}

            {errorMessage && (
              <div className="error-banner">
                <span className="error-icon">⚠️</span>
                <div>
                  <strong>Connection Error:</strong> {errorMessage}
                  <p className="error-hint">Ensure the FastAPI backend is running on <code>http://localhost:8000</code>.</p>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="initialization-card">
          <div className="section-header">
            <h2>Forecast Analytics Initialization</h2>
            <span className="badge badge-neutral">Phase 2 — Project Scaffold</span>
          </div>
          <p className="init-description">
            The core full-stack application shell and health verification endpoints are initialized.
            To maintain strict data integrity, no fabricated or simulated metrics are displayed.
            Analytical evaluation components will be activated in subsequent phases upon ingestion of verified
            Elexon datasets.
          </p>
          <div className="pipeline-steps">
            <div className="pipeline-step step-complete">
              <span className="step-num">1</span>
              <div>
                <h4>Environment & API Audit</h4>
                <p>Verified FUELHH and WINDFOR streams and environment capabilities.</p>
              </div>
            </div>
            <div className="pipeline-step step-current">
              <span className="step-num">2</span>
              <div>
                <h4>Project Initialization</h4>
                <p>Vite React frontend, FastAPI backend, Docker Compose, and CI pipeline.</p>
              </div>
            </div>
            <div className="pipeline-step step-upcoming">
              <span className="step-num">3</span>
              <div>
                <h4>Leak-Free Ingestion & Metrics</h4>
                <p>Cutoff-based forecast revision selection, half-hour aggregation, and MAE/RMSE/WAPE metrics.</p>
              </div>
            </div>
            <div className="pipeline-step step-upcoming">
              <span className="step-num">4</span>
              <div>
                <h4>Interactive Trading Dashboard</h4>
                <p>Time-series actual vs forecast overlays, residual error distributions, and cutoff controls.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>
          Data Sources: Elexon BMRS{' '}
          <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream" target="_blank" rel="noreferrer">
            FUELHH (Actuals)
          </a>{' '}
          &amp;{' '}
          <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream" target="_blank" rel="noreferrer">
            WINDFOR (Forecasts)
          </a>
          . For day-ahead power purchasing decisions in January 2026.
        </p>
      </footer>
    </div>
  );
}
