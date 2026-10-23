export default function EmptyState({
  title = 'No Matched Observations Found',
  message = 'No delivery intervals had both an eligible pre-cutoff forecast and complete actual generation for the configured parameters.',
  onReset,
}) {
  return (
    <div className="state-card empty-state" role="status">
      <div className="state-icon-wrapper empty-icon-wrapper">
        <span className="state-icon">🔍</span>
      </div>

      <h3 className="state-title">{title}</h3>
      <p className="state-message">{message}</p>

      <div className="empty-explanation">
        <ul>
          <li>Verify that decision dates fall within January 1–31, 2026.</li>
          <li>Ensure the decision cutoff allows at least one forecast publication run before the cutoff time.</li>
          <li>Incomplete half-hourly actuals or missing forecasts are excluded to maintain statistical integrity.</li>
        </ul>
      </div>

      {onReset && (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onReset}
        >
          Reset to Default January Parameters
        </button>
      )}
    </div>
  );
}
