import { useEffect, useState } from 'react';
import { formatUTCDateTime } from '../utils/formatters';

export default function AppHeader({
  healthStatus,
  onCheckHealth,
  cacheMetadata,
  configuredCutoff = '09:50',
}) {
  const [currentUtcTime, setCurrentUtcTime] = useState(() =>
    new Date().toISOString()
  );

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentUtcTime(new Date().toISOString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="app-header">
      <div className="header-top">
        <div className="brand-group">
          <div className="brand-logo">
            <span className="logo-icon" aria-hidden="true">⚡</span>
            <div>
              <h1 className="brand-title">Wind Forecast Insights</h1>
              <p className="brand-subtitle">
                UK Day-Ahead Electricity Market Wind-Generation Forecast Evaluation
              </p>
            </div>
          </div>
        </div>

        <div className="header-indicators">
          {/* Real Backend Health Status Indicator */}
          <div
            className={`status-pill status-${healthStatus}`}
            title={`Backend connectivity status: ${healthStatus}`}
            role="status"
          >
            <span className="status-dot"></span>
            <span className="status-label">
              {healthStatus === 'loading' && 'Checking Backend...'}
              {healthStatus === 'available' && 'Backend Connected'}
              {healthStatus === 'unavailable' && 'Backend Offline'}
            </span>
            <button
              type="button"
              className="btn-icon-refresh"
              onClick={onCheckHealth}
              title="Re-check backend connection"
              aria-label="Re-check backend connection"
              disabled={healthStatus === 'loading'}
            >
              ↻
            </button>
          </div>

          {/* Response Cache / Data Freshness Indicator */}
          {cacheMetadata && (
            <div
              className={`cache-pill ${cacheMetadata.cached ? 'cache-hit' : 'cache-fresh'}`}
              title={
                cacheMetadata.cached
                  ? `Response served from memory cache (TTL: ${cacheMetadata.cache_ttl_seconds}s)`
                  : 'Response newly computed from source datasets'
              }
            >
              <span className="cache-icon">{cacheMetadata.cached ? '⚡' : '●'}</span>
              <span className="cache-label">
                {cacheMetadata.cached ? 'Cached Analysis' : 'Live Elexon Ingestion'}
              </span>
              {cacheMetadata.data_retrieval_timestamp && (
                <span className="cache-time">
                  Retrieved: {formatUTCDateTime(cacheMetadata.data_retrieval_timestamp, true)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Temporal Distinction: Historical Cutoff vs Current Live Clock */}
      <div className="header-temporal-bar" role="region" aria-label="Temporal Context">
        <div className="temporal-item">
          <span className="temporal-label">Configured Sample Decision Cutoff:</span>
          <span className="temporal-value cutoff-highlight">
            {configuredCutoff} UTC on D-1
          </span>
          <span className="temporal-note">(Sample N2EX Day-Ahead auction clearing assumption)</span>
        </div>
        <div className="temporal-item clock-item">
          <span className="temporal-label">Current UTC Clock:</span>
          <span className="temporal-value system-clock">
            {formatUTCDateTime(currentUtcTime, true)}
          </span>
        </div>
      </div>
    </header>
  );
}
