import { useState } from 'react';
import { formatCount } from '../utils/formatters';

export default function DataQualityPanel({ dataQuality }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!dataQuality) return null;

  const {
    raw_fuelhh_count,
    raw_windfor_count,
    selected_forecast_count,
    excluded_leakage_count,
    hourly_actual_count,
    matched_count,
    missing_actual_count,
    missing_forecast_count,
    missing_both_count,
  } = dataQuality;

  return (
    <section className="data-quality-panel" aria-labelledby="dq-heading">
      <div className="dq-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="dq-header-text">
          <h3 id="dq-heading" className="dq-title">
            Data Quality & Ingestion Audit
          </h3>
          <p className="dq-subtitle">
            Elexon FUELHH & WINDFOR stream pipeline counters and pairing reconciliation.
          </p>
        </div>
        <button
          type="button"
          className="btn-toggle-expand"
          aria-expanded={isExpanded}
          aria-controls="dq-details-grid"
        >
          {isExpanded ? 'Hide Details ▲' : 'Show Details ▼'}
        </button>
      </div>

      {/* Summary Highlights (Always Visible) */}
      <div className="dq-summary-pills">
        <div className="dq-pill">
          <span className="dq-pill-label">Raw Elexon Streams:</span>
          <span className="dq-pill-val">
            {formatCount(raw_fuelhh_count)} actuals / {formatCount(raw_windfor_count)} forecasts
          </span>
        </div>
        <div className="dq-pill pill-leakage">
          <span className="dq-pill-label">Post-Cutoff Excluded:</span>
          <span className="dq-pill-val">{formatCount(excluded_leakage_count)} revisions</span>
        </div>
        <div className="dq-pill">
          <span className="dq-pill-label">Paired Matched Hours:</span>
          <span className="dq-pill-val">{formatCount(matched_count)} hours</span>
        </div>
        {(missing_actual_count > 0 || missing_forecast_count > 0 || missing_both_count > 0) && (
          <div className="dq-pill pill-warning">
            <span className="dq-pill-label">Incomplete Periods:</span>
            <span className="dq-pill-val">
              {formatCount(missing_forecast_count + missing_actual_count + missing_both_count)} excluded
            </span>
          </div>
        )}
      </div>

      {/* Collapsible Detailed Grid */}
      {isExpanded && (
        <div id="dq-details-grid" className="dq-grid">
          <div className="dq-card">
            <span className="dq-card-label">Raw FUELHH Records</span>
            <span className="dq-card-value">{formatCount(raw_fuelhh_count)}</span>
            <span className="dq-card-desc">Half-hourly outturn readings (fuelType=WIND)</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Hourly Actual Periods</span>
            <span className="dq-card-value">{formatCount(hourly_actual_count)}</span>
            <span className="dq-card-desc">Pairs of :00 and :30 half-hours averaged to 1h</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Raw WINDFOR Records</span>
            <span className="dq-card-value">{formatCount(raw_windfor_count)}</span>
            <span className="dq-card-desc">Total forecast records across rolling 72h horizons</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Selected Pre-Cutoff Forecasts</span>
            <span className="dq-card-value">{formatCount(selected_forecast_count)}</span>
            <span className="dq-card-desc">Distinct target hours with eligible pre-cutoff revision</span>
          </div>

          <div className="dq-card card-excluded">
            <span className="dq-card-label">Excluded Future Revisions</span>
            <span className="dq-card-value">{formatCount(excluded_leakage_count)}</span>
            <span className="dq-card-desc">Revisions published after D-1 cutoff (strict anti-leakage)</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Matched Observations</span>
            <span className="dq-card-value">{formatCount(matched_count)}</span>
            <span className="dq-card-desc">Evaluated paired delivery intervals</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Missing Forecasts</span>
            <span className="dq-card-value">{formatCount(missing_forecast_count)}</span>
            <span className="dq-card-desc">Actual exists, but no forecast before cutoff</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Missing Actuals</span>
            <span className="dq-card-value">{formatCount(missing_actual_count)}</span>
            <span className="dq-card-desc">Forecast exists, but incomplete outturn</span>
          </div>

          <div className="dq-card">
            <span className="dq-card-label">Missing Both Streams</span>
            <span className="dq-card-value">{formatCount(missing_both_count)}</span>
            <span className="dq-card-desc">Neither forecast nor actual available</span>
          </div>

          <div className="dq-notice-box">
            <p>
              ℹ️ <strong>Data Integrity Standard:</strong> Incomplete periods are strictly excluded from paired accuracy metric calculations (MAE, RMSE, MBE, WAPE) rather than being falsely imputed as zero-generation values.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
