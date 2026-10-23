import { useState, useMemo } from 'react';

/**
 * Calculates delivery date (D+1) for a given decision date string (YYYY-MM-DD).
 */
function deriveDeliveryDate(dateStr) {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return '—';
  try {
    const parts = dateStr.split('-').map(Number);
    const d = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2] + 1));
    return d.toISOString().slice(0, 10);
  } catch {
    return '—';
  }
}

export default function AnalysisFilters({
  appliedFilters,
  onApplyFilters,
  onRefresh,
  isLoading = false,
}) {
  // Local draft state — changing controls does not trigger network requests until applied
  const [draftStart, setDraftStart] = useState(appliedFilters.decision_start_date);
  const [draftEnd, setDraftEnd] = useState(appliedFilters.decision_end_date);
  const [draftCutoff, setDraftCutoff] = useState(appliedFilters.cutoff_time);
  const [validationError, setValidationError] = useState(null);

  // Derived effective delivery dates based on draft selection
  const draftDeliveryStart = useMemo(() => deriveDeliveryDate(draftStart), [draftStart]);
  const draftDeliveryEnd = useMemo(() => deriveDeliveryDate(draftEnd), [draftEnd]);

  // Derived effective delivery dates based on currently applied selection
  const appliedDeliveryStart = useMemo(
    () => deriveDeliveryDate(appliedFilters.decision_start_date),
    [appliedFilters.decision_start_date]
  );
  const appliedDeliveryEnd = useMemo(
    () => deriveDeliveryDate(appliedFilters.decision_end_date),
    [appliedFilters.decision_end_date]
  );

  const isDirty =
    draftStart !== appliedFilters.decision_start_date ||
    draftEnd !== appliedFilters.decision_end_date ||
    draftCutoff !== appliedFilters.cutoff_time;

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError(null);

    // Validation
    if (!draftStart || !draftEnd) {
      setValidationError('Both decision start and end dates are required.');
      return;
    }
    if (draftStart > draftEnd) {
      setValidationError('Decision start date cannot be after decision end date.');
      return;
    }
    if (draftStart < '2026-01-01' || draftStart > '2026-01-31') {
      setValidationError('Decision start date must be within January 2026 (2026-01-01 to 2026-01-31).');
      return;
    }
    if (draftEnd < '2026-01-01' || draftEnd > '2026-01-31') {
      setValidationError('Decision end date must be within January 2026 (2026-01-01 to 2026-01-31).');
      return;
    }
    if (!/^\d{2}:\d{2}$/.test(draftCutoff)) {
      setValidationError('Cutoff time must be in HH:MM format (24-hour UTC).');
      return;
    }
    const [h, m] = draftCutoff.split(':').map(Number);
    if (h < 0 || h > 23 || m < 0 || m > 59) {
      setValidationError('Cutoff time hours must be 00-23 and minutes 00-59.');
      return;
    }

    onApplyFilters({
      decision_start_date: draftStart,
      decision_end_date: draftEnd,
      cutoff_time: draftCutoff,
    });
  };

  const handleResetToDefaults = () => {
    setDraftStart('2026-01-01');
    setDraftEnd('2026-01-31');
    setDraftCutoff('09:50');
    setValidationError(null);
  };

  return (
    <section className="filters-card" aria-labelledby="filters-heading">
      <div className="filters-header">
        <div>
          <h2 id="filters-heading" className="filters-title">
            Trading Decision Parameters
          </h2>
          <p className="filters-subtitle">
            Configure Day-Ahead decision evaluation boundaries (January 1–31, 2026).
            Controls specify when purchasing contracts were cleared, not physical delivery dates.
          </p>
        </div>
        <div className="applied-tag-group">
          <span className="applied-badge">
            Active Cutoff: <strong>{appliedFilters.cutoff_time} UTC</strong>
          </span>
          <span className="applied-badge">
            Decision: <strong>{appliedFilters.decision_start_date}</strong> to <strong>{appliedFilters.decision_end_date}</strong>
          </span>
          <span className="applied-badge">
            Delivery: <strong>{appliedDeliveryStart}</strong> to <strong>{appliedDeliveryEnd}</strong>
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="filters-form">
        <div className="filter-fields-row">
          {/* Decision Start Date */}
          <div className="form-group">
            <label htmlFor="filter-start-date" className="form-label">
              Decision Start Date (D-1)
            </label>
            <input
              id="filter-start-date"
              type="date"
              className="form-input"
              min="2026-01-01"
              max="2026-01-31"
              value={draftStart}
              onChange={(e) => setDraftStart(e.target.value)}
              required
            />
            <span className="form-help">Contract decision day in Jan 2026</span>
          </div>

          {/* Decision End Date */}
          <div className="form-group">
            <label htmlFor="filter-end-date" className="form-label">
              Decision End Date (D-1)
            </label>
            <input
              id="filter-end-date"
              type="date"
              className="form-input"
              min="2026-01-01"
              max="2026-01-31"
              value={draftEnd}
              onChange={(e) => setDraftEnd(e.target.value)}
              required
            />
            <span className="form-help">Final decision day in Jan 2026</span>
          </div>

          {/* Cutoff Time */}
          <div className="form-group">
            <label htmlFor="filter-cutoff-time" className="form-label">
              Decision Cutoff Time (UTC)
            </label>
            <input
              id="filter-cutoff-time"
              type="text"
              className="form-input cutoff-input"
              pattern="^\d{2}:\d{2}$"
              placeholder="09:50"
              maxLength={5}
              value={draftCutoff}
              onChange={(e) => setDraftCutoff(e.target.value)}
              required
            />
            <span className="form-help">Sample N2EX auction cutoff (09:50 default)</span>
          </div>

          {/* Derived Effective Delivery Range Display */}
          <div className="delivery-horizon-card">
            <span className="horizon-label">Effective Delivery Window (D+1)</span>
            <div className="horizon-value">
              <span>{draftDeliveryStart}</span>
              <span className="horizon-arrow">→</span>
              <span>{draftDeliveryEnd}</span>
            </div>
            <span className="horizon-hint">
              Physical generation delivered next day
            </span>
          </div>
        </div>

        {validationError && (
          <div className="filter-error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <span>{validationError}</span>
          </div>
        )}

        <div className="filter-actions-row">
          <div className="action-buttons-left">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading && !isDirty}
              id="apply-filters-btn"
            >
              {isLoading && !isDirty ? 'Running Analysis...' : isDirty ? 'Apply Parameters' : 'Run Analysis'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onRefresh}
              disabled={isLoading}
              id="refresh-analysis-btn"
              title="Re-run analysis for currently applied parameters"
            >
              {isLoading ? 'Refreshing...' : 'Refresh Analysis'}
            </button>
          </div>

          {isDirty && (
            <button
              type="button"
              className="btn-link"
              onClick={handleResetToDefaults}
              disabled={isLoading}
            >
              Reset Inputs
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
