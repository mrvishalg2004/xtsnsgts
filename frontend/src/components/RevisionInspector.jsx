import { useEffect } from 'react';
import {
  formatMW,
  formatUTCDateTime,
  formatCount,
  getRevisionStatusBadge,
} from '../utils/formatters';

export default function RevisionInspector({
  isOpen,
  onClose,
  targetStartTime,
  cutoffTime,
  data,
  isLoading,
  error,
}) {
  // Listen for Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const {
    target_start_time,
    delivery_date,
    decision_date,
    decision_cutoff,
    total_revisions,
    eligible_revisions_count,
    selected_revision,
    revisions = [],
  } = data || {};

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="inspector-modal-title"
    >
      <div
        className="inspector-modal"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
      >
        <div className="inspector-modal-header">
          <div>
            <span className="inspector-kicker">Elexon WINDFOR Revision Audit</span>
            <h2 id="inspector-modal-title" className="inspector-title">
              Forecast Revision History
            </h2>
            <p className="inspector-subtitle">
              Target Delivery: <strong>{formatUTCDateTime(targetStartTime || target_start_time)}</strong>
            </p>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close revision inspector"
          >
            ✕
          </button>
        </div>

        <div className="inspector-modal-body">
          {isLoading && (
            <div className="inspector-loading">
              <span className="spinner"></span>
              <p>Fetching historical WINDFOR publication runs from Elexon...</p>
            </div>
          )}

          {error && (
            <div className="inspector-error" role="alert">
              <span className="error-icon">⚠️</span>
              <div>
                <strong>Failed to load revisions:</strong> {error}
                <p className="error-hint">
                  The delivery period may be out of scope or upstream Elexon data was unavailable.
                </p>
              </div>
            </div>
          )}

          {!isLoading && !error && data && (
            <>
              {/* Context metadata grid */}
              <div className="inspector-meta-grid">
                <div className="meta-box">
                  <span className="meta-label">Delivery Date</span>
                  <span className="meta-val">{delivery_date || '—'}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-label">Decision Date (D-1)</span>
                  <span className="meta-val">{decision_date || '—'}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-label">Decision Cutoff</span>
                  <span className="meta-val cutoff-text">
                    {formatUTCDateTime(decision_cutoff)}
                  </span>
                </div>
                <div className="meta-box">
                  <span className="meta-label">Total Revisions</span>
                  <span className="meta-val">{formatCount(total_revisions)}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-label">Eligible (Pre-Cutoff)</span>
                  <span className="meta-val text-success">
                    {formatCount(eligible_revisions_count)}
                  </span>
                </div>
                <div className="meta-box">
                  <span className="meta-label">Excluded (Post-Cutoff)</span>
                  <span className="meta-val text-warning">
                    {formatCount(total_revisions - eligible_revisions_count)}
                  </span>
                </div>
              </div>

              {/* Selected Benchmark Spotlight */}
              {selected_revision ? (
                <div className="selected-benchmark-card">
                  <div className="benchmark-header">
                    <span className="benchmark-badge">⭐ Selected Day-Ahead Benchmark</span>
                    <span className="benchmark-note">
                      Used in accuracy evaluation and timeseries
                    </span>
                  </div>
                  <div className="benchmark-details">
                    <div className="benchmark-stat">
                      <span className="stat-label">Forecast Generation:</span>
                      <span className="stat-value font-mono">
                        {formatMW(selected_revision.forecast_generation_mw, 1, true)}
                      </span>
                    </div>
                    <div className="benchmark-stat">
                      <span className="stat-label">Published At:</span>
                      <span className="stat-value font-mono">
                        {formatUTCDateTime(selected_revision.publish_time, true)}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="no-benchmark-card">
                  <span className="badge-status-missing-forecast">No Eligible Revision</span>
                  <p>
                    No forecast was published by Elexon for this target delivery hour prior to the {cutoffTime} UTC decision cutoff.
                    This delivery period is correctly excluded from paired metrics.
                  </p>
                </div>
              )}

              {/* Revision History Chronological List */}
              <div className="revisions-list-section">
                <h3 className="section-title">
                  All WINDFOR Publication Runs ({revisions.length})
                </h3>
                <p className="section-caption">
                  Chronological order of publications. Strictly distinguishes eligible pre-cutoff forecasts from post-cutoff forecasts to prevent future-data leakage.
                </p>

                {revisions.length === 0 ? (
                  <p className="empty-revisions-text">No publication records found for this hour.</p>
                ) : (
                  <div className="revisions-table-wrapper">
                    <table className="revisions-table">
                      <thead>
                        <tr>
                          <th scope="col">Publication Time (UTC)</th>
                          <th scope="col" className="num-col">Forecast (MW)</th>
                          <th scope="col">Eligibility</th>
                          <th scope="col">Evaluation Role</th>
                        </tr>
                      </thead>
                      <tbody>
                        {revisions.map((rev, idx) => {
                          const badge = getRevisionStatusBadge(rev.status_reason);
                          return (
                            <tr
                              key={`${rev.publish_time}-${idx}`}
                              className={`revision-row ${
                                rev.is_selected
                                  ? 'row-selected-revision'
                                  : !rev.is_eligible
                                  ? 'row-excluded-revision'
                                  : ''
                              }`}
                            >
                              <td className="font-mono">
                                {formatUTCDateTime(rev.publish_time, true)}
                              </td>
                              <td className="num-col font-mono">
                                {formatMW(rev.forecast_generation_mw, 1)}
                              </td>
                              <td>
                                <span
                                  className={`eligibility-badge ${
                                    rev.is_eligible ? 'badge-eligible' : 'badge-ineligible'
                                  }`}
                                >
                                  {rev.is_eligible ? 'Eligible (≤ Cutoff)' : 'Ineligible (> Cutoff)'}
                                </span>
                              </td>
                              <td>
                                <span className={`revision-badge ${badge.className}`}>
                                  {badge.label}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="inspector-modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
