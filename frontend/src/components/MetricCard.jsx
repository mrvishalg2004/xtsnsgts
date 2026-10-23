import { formatMW, formatSignedMW, formatPercent, formatCount } from '../utils/formatters';

export function MetricCard({
  id,
  title,
  value,
  unit,
  subtitle,
  explanation,
  variant = 'default',
  badgeText = null,
  badgeVariant = 'neutral',
}) {
  return (
    <div className={`metric-card metric-${variant}`} id={id}>
      <div className="metric-header">
        <span className="metric-title">{title}</span>
        {badgeText && (
          <span className={`metric-badge badge-${badgeVariant}`}>{badgeText}</span>
        )}
      </div>

      <div className="metric-value-row">
        <span className="metric-value">{value}</span>
        {unit && value !== '—' && <span className="metric-unit">{unit}</span>}
      </div>

      {subtitle && <div className="metric-subtitle">{subtitle}</div>}

      {explanation && (
        <div className="metric-explanation">
          <p>{explanation}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Grid component rendering the 5 standard wholesale evaluation KPIs.
 */
export default function KpiMetricsGrid({ metrics, dataQuality }) {
  if (!metrics) {
    return (
      <div className="metrics-grid skeleton-grid">
        <div className="metric-card skeleton-card"></div>
        <div className="metric-card skeleton-card"></div>
        <div className="metric-card skeleton-card"></div>
        <div className="metric-card skeleton-card"></div>
        <div className="metric-card skeleton-card"></div>
      </div>
    );
  }

  const { mae, rmse, mbe, wape, matched_count } = metrics;

  // Classify MBE bias direction
  let mbeVariant = 'default';
  let mbeBadge = null;
  let mbeBadgeVariant = 'neutral';
  let mbeSubtitle = 'Average signed forecast error';

  if (mbe !== null && mbe !== undefined && !isNaN(mbe)) {
    const numMbe = Number(mbe);
    if (numMbe > 0.05) {
      mbeVariant = 'positive-bias';
      mbeBadge = 'Over-Forecast Bias';
      mbeBadgeVariant = 'warning';
      mbeSubtitle = 'Forecast exceeded actual outturn on average';
    } else if (numMbe < -0.05) {
      mbeVariant = 'negative-bias';
      mbeBadge = 'Under-Forecast Bias';
      mbeBadgeVariant = 'info';
      mbeSubtitle = 'Forecast was lower than actual outturn on average';
    } else {
      mbeVariant = 'zero-bias';
      mbeBadge = 'Zero Bias';
      mbeBadgeVariant = 'success';
      mbeSubtitle = 'Zero average signed error';
    }
  }

  return (
    <section className="kpi-section" aria-labelledby="kpi-heading">
      <div className="section-title-row">
        <div>
          <h2 id="kpi-heading" className="section-heading">
            Key Forecast Accuracy Indicators
          </h2>
          <p className="section-subheading">
            Paired evaluation of day-ahead forecasts against complete hourly actual outturns across {formatCount(matched_count)} matched delivery periods.
          </p>
        </div>
      </div>

      <div className="metrics-grid">
        {/* 1. MAE */}
        <MetricCard
          id="kpi-mae"
          title="Mean Absolute Error (MAE)"
          value={formatMW(mae, 1)}
          unit="MW"
          subtitle="Average magnitude of hourly forecast deviations"
          explanation="Measures the average absolute deviation between forecast generation and actual delivery outturn, weighting all error magnitudes linearly."
        />

        {/* 2. RMSE */}
        <MetricCard
          id="kpi-rmse"
          title="Root Mean Squared Error (RMSE)"
          value={formatMW(rmse, 1)}
          unit="MW"
          subtitle="Variance-weighted deviation penalizing large misses"
          explanation="Quadratic error metric that penalizes large forecast misses more severely than small deviations. Always greater than or equal to MAE."
        />

        {/* 3. MBE */}
        <MetricCard
          id="kpi-mbe"
          title="Mean Bias Error (MBE)"
          value={formatSignedMW(mbe, 1)}
          unit="MW"
          subtitle={mbeSubtitle}
          badgeText={mbeBadge}
          badgeVariant={mbeBadgeVariant}
          variant={mbeVariant}
          explanation="Signed average error (forecast − actual). Positive bias denotes systematic over-forecasting; negative bias denotes persistent under-forecasting."
        />

        {/* 4. WAPE */}
        <MetricCard
          id="kpi-wape"
          title="Weighted Absolute Percentage Error (WAPE)"
          value={formatPercent(wape, 2)}
          unit=""
          subtitle="Total absolute error as percentage of total actual generation"
          explanation="Volume-weighted error percentage (∑|Error| / ∑Actual × 100%). Avoids distortion from low-generation hours compared to standard MAPE."
        />

        {/* 5. Matched Observations */}
        <MetricCard
          id="kpi-matched-count"
          title="Matched Delivery Hours"
          value={formatCount(matched_count)}
          unit="hours"
          subtitle={
            dataQuality?.missing_forecast_count || dataQuality?.missing_actual_count
              ? `${dataQuality.missing_forecast_count} missing forecasts, ${dataQuality.missing_actual_count} missing actuals`
              : 'Complete paired observations evaluated'
          }
          explanation={`Statistical basis for the metrics above. Only hours with both an eligible forecast published prior to cutoff and complete actual outturn are evaluated.`}
        />
      </div>
    </section>
  );
}
