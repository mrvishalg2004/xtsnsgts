import { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import {
  formatMW,
  formatSignedMW,
  formatUTCDateTime,
} from '../utils/formatters';

function CustomErrorTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  const dataPoint = payload[0]?.payload;
  if (!dataPoint || dataPoint.error_mw === null || dataPoint.error_mw === undefined) {
    return null;
  }

  const error = Number(dataPoint.error_mw);
  const isPositive = error > 0;
  const isNegative = error < 0;

  return (
    <div className="chart-tooltip">
      <div className="tooltip-header">
        <span className="tooltip-title">
          {formatUTCDateTime(dataPoint.target_start_time)}
        </span>
        <span
          className={`tooltip-badge ${
            isPositive
              ? 'badge-overforecast'
              : isNegative
              ? 'badge-underforecast'
              : 'badge-zerobias'
          }`}
        >
          {isPositive ? 'Over-Forecast (+)' : isNegative ? 'Under-Forecast (−)' : 'Zero Error'}
        </span>
      </div>

      <div className="tooltip-body">
        <div className="tooltip-row">
          <span className="tooltip-label">Signed Error (F − A):</span>
          <span
            className={`tooltip-value ${
              isPositive ? 'val-positive' : isNegative ? 'val-negative' : ''
            }`}
          >
            {formatSignedMW(error, 1, true)}
          </span>
        </div>

        <div className="tooltip-error-explanation">
          {isPositive && (
            <p>
              Forecast generation exceeded actual delivery by{' '}
              <strong>{formatMW(Math.abs(error), 1, true)}</strong>.
            </p>
          )}
          {isNegative && (
            <p>
              Forecast generation was lower than actual delivery by{' '}
              <strong>{formatMW(Math.abs(error), 1, true)}</strong>.
            </p>
          )}
          {!isPositive && !isNegative && (
            <p>Forecast generation matched actual delivery exactly.</p>
          )}
        </div>

        <div className="tooltip-divider"></div>

        <div className="tooltip-row">
          <span className="tooltip-label">Forecast:</span>
          <span className="tooltip-value">
            {formatMW(dataPoint.forecast_generation_mw, 1, true)}
          </span>
        </div>

        <div className="tooltip-row">
          <span className="tooltip-label">Actual:</span>
          <span className="tooltip-value">
            {formatMW(dataPoint.actual_generation_mw, 1, true)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ForecastErrorChart({ records = [] }) {
  // Filter to records with valid numeric error_mw for the residual chart
  const errorData = useMemo(() => {
    if (!records) return [];
    return records.filter(
      (r) => r.error_mw !== null && r.error_mw !== undefined && !isNaN(r.error_mw)
    );
  }, [records]);

  const formatXAxisTick = (isoTime) => {
    if (!isoTime) return '';
    try {
      const d = new Date(isoTime);
      const day = String(d.getUTCDate()).padStart(2, '0');
      const month = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' });
      const hours = String(d.getUTCHours()).padStart(2, '0');
      if (hours === '00') {
        return `${day} ${month}`;
      }
      return `${hours}:00`;
    } catch {
      return isoTime;
    }
  };

  if (!errorData || errorData.length === 0) {
    return (
      <div className="chart-card empty-chart-card">
        <h3>Hourly Forecast Error (Residuals)</h3>
        <p className="chart-empty-message">
          No paired observations with valid forecast and actual values to compute errors.
        </p>
      </div>
    );
  }

  return (
    <section className="chart-card" aria-labelledby="error-chart-heading">
      <div className="chart-header">
        <div>
          <h2 id="error-chart-heading" className="chart-title">
            Hourly Forecast Error (Signed Residuals: Forecast − Actual)
          </h2>
          <p className="chart-subtitle">
            Positive values indicate over-forecasting (forecast &gt; actual); negative values indicate under-forecasting (forecast &lt; actual).
          </p>
        </div>

        <div className="error-legend-badges">
          <span className="legend-badge-item">
            <span className="legend-color-swatch swatch-overforecast"></span>
            Over-Forecast (&gt; 0 MW)
          </span>
          <span className="legend-badge-item">
            <span className="legend-color-swatch swatch-underforecast"></span>
            Under-Forecast (&lt; 0 MW)
          </span>
        </div>
      </div>

      <div className="chart-wrapper" style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={errorData}
            margin={{ top: 12, right: 24, left: 16, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#263554" vertical={false} />

            <XAxis
              dataKey="target_start_time"
              tickFormatter={formatXAxisTick}
              stroke="#647b9f"
              tick={{ fill: '#9bb0d3', fontSize: 12 }}
              minTickGap={45}
            />

            <YAxis
              stroke="#647b9f"
              tick={{ fill: '#9bb0d3', fontSize: 12 }}
              unit=" MW"
              width={80}
              tickFormatter={(v) => Number(v).toLocaleString('en-GB')}
            />

            <Tooltip content={<CustomErrorTooltip />} />

            <ReferenceLine y={0} stroke="#9bb0d3" strokeWidth={1.5} />

            <Bar dataKey="error_mw" name="Signed Error" isAnimationActive={false}>
              {errorData.map((entry) => (
                <Cell
                  key={`cell-${entry.target_start_time}`}
                  fill={entry.error_mw >= 0 ? '#ffab00' : '#7c4dff'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer-caption">
        <span>
          Preserves signed error magnitude in MW. Zero reference line highlights shifts between systemic over-forecast and under-forecast regimes.
        </span>
      </div>
    </section>
  );
}
