export default function ErrorState({
  title = 'Analysis Evaluation Failed',
  error,
  onRetry,
}) {
  const errorMessage = error?.message || (typeof error === 'string' ? error : 'An unexpected error occurred');
  const errorStatus = error?.status;
  const isUpstream = errorStatus === 502 || errorStatus === 504 || (errorMessage && errorMessage.includes('upstream'));
  const isNetwork = errorStatus === 0 || (errorMessage && errorMessage.includes('communicate with the analytics backend'));

  return (
    <div className="state-card error-state" role="alert">
      <div className="state-icon-wrapper error-icon-wrapper">
        <span className="state-icon">⚠️</span>
      </div>

      <h3 className="state-title">{title}</h3>
      <p className="state-message">{errorMessage}</p>

      {errorStatus ? (
        <div className="error-meta-badge">
          HTTP Status: <strong>{errorStatus}</strong>
        </div>
      ) : null}

      <div className="error-guidance-box">
        {isNetwork && (
          <p>
            The browser could not reach the FastAPI backend service. Ensure the backend server is running on{' '}
            <code>http://localhost:8000</code> or verify <code>VITE_API_BASE_URL</code>.
          </p>
        )}
        {isUpstream && (
          <p>
            The backend reported an upstream issue contacting official Elexon BMRS datasets.
            This may occur if Elexon services are temporarily throttling or undergoing maintenance.
          </p>
        )}
        {!isNetwork && !isUpstream && (
          <p>
            Please verify your query parameters or retry the analysis.
          </p>
        )}
      </div>

      {onRetry && (
        <button
          type="button"
          className="btn btn-primary btn-retry"
          onClick={onRetry}
        >
          ↻ Retry Analysis
        </button>
      )}
    </div>
  );
}
