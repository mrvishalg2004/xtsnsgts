export default function LoadingState({
  title = 'Computing Forecast Evaluation...',
  message = 'Ingesting official Elexon FUELHH and WINDFOR streams and evaluating decision-cutoff benchmarks.',
}) {
  return (
    <div className="state-card loading-state" role="status" aria-live="polite">
      <div className="spinner-large"></div>
      <h3 className="state-title">{title}</h3>
      <p className="state-message">{message}</p>
      <div className="loading-progress-hints">
        <span className="hint-pill">Querying Elexon streams</span>
        <span className="hint-pill">Aggregating half-hourly actuals</span>
        <span className="hint-pill">Applying anti-leakage cutoffs</span>
      </div>
    </div>
  );
}
