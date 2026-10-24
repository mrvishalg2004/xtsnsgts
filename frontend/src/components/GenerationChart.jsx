import { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  formatMW,
  formatSignedMW,
  formatUTCDateTime,
  getAvailabilityBadge,
} from '../utils/formatters';

/**
 * Custom tooltip rendering detailed contextual information for each delivery period.
 */
function CustomGenerationTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  const dataPoint = payload[0]?.payload;
  if (!dataPoint) return null;

  const badge = getAvailabilityBadge(dataPoint.availability_status);

  return (
    <div className="chart-tooltip">
      <div className="tooltip-header">
        <span className="tooltip-title">
          {formatUTCDateTime(dataPoint.target_start_time)}
        </span>
        <span className={`tooltip-badge ${badge.className}`}>{badge.label}</span>
      </div>

      <div className="tooltip-body">
        <div className="tooltip-row">
          <span className="tooltip-dot dot-forecast"></span>
          <span className="tooltip-label">Day-Ahead Forecast:</span>
          <span className="tooltip-value">
            {formatMW(dataPoint.forecast_generation_mw, 1, true)}
          </span>
        </div>

        <div className="tooltip-row">
          <span className="tooltip-dot dot-actual"></span>
          <span className="tooltip-label">Actual Generation:</span>
          <span className="tooltip-value">
            {formatMW(dataPoint.actual_generation_mw, 1, true)}
          </span>
        </div>

        {dataPoint.error_mw !== null && dataPoint.error_mw !== undefined && (
          <div className="tooltip-row tooltip-error-row">
            <span className="tooltip-label">Forecast Error (F − A):</span>
            <span
              className={`tooltip-value ${
                dataPoint.error_mw > 0
                  ? 'val-positive'
                  : dataPoint.error_mw < 0
                  ? 'val-negative'
                  : ''
              }`}
            >
              {formatSignedMW(dataPoint.error_mw, 1, true)}
            </span>
          </div>
        )}

        <div className="tooltip-divider"></div>

        <div className="tooltip-meta-row">
          <span className="tooltip-meta-label">Forecast Published:</span>
          <span className="tooltip-meta-value">
            {formatUTCDateTime(dataPoint.forecast_publish_time)}
          </span>
        </div>

        <div className="tooltip-meta-row">
          <span className="tooltip-meta-label">Decision Cutoff:</span>
          <span className="tooltip-meta-value">
            {formatUTCDateTime(dataPoint.decision_cutoff)}
          </span>
        </div>
      </div>

      <div className="tooltip-hint">Click point to inspect forecast revisions</div>
    </div>
  );
}

export default function GenerationChart({
  records = [],
  onSelectTimestamp = null,
  _selectedTimestamp = null,
}) {
  // Optional zoom/focus range selector or display resolution
  const [visibleSlice, setVisibleSlice] = useState('all'); // 'all' | 'first-week' | 'first-day'

  const chartData = useMemo(() => {
    if (!records || !records.length) return [];
    if (visibleSlice === 'first-day') {
      return records.slice(0, 24);
    }
    if (visibleSlice === 'first-week') {
      return records.slice(0, 168);
    }
    return records;
  }, [records, visibleSlice]);

  // Format tick labels on X-Axis to prevent overlap across 744 hours
  const formatXAxisTick = (isoTime) => {
    if (!isoTime) return '';
    try {
      const d = new Date(isoTime);
      const day = String(d.getUTCDate()).padStart(2, '0');
      const month = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' });
      const hours = String(d.getUTCHours()).padStart(2, '0');

      if (chartData.length <= 24) {
        // High resolution (24h Sample): show clean hourly tick "HH:00"
        return `${hours}:00`;
      }
      if (chartData.length <= 168) {
        // Medium resolution (First 7 Days): show date at midnight, otherwise hour
        if (hours === '00') {
          return `${day} ${month}`;
        }
        return `${hours}:00`;
      }
      // Full Window (month): show date transition clearly to avoid ambiguous time-of-day labels
      if (hours === '00') {
        return `${day} ${month}`;
      }
      return `${day} ${month} ${hours}:00`;
    } catch {
      return isoTime;
    }
  };

  const handlePointClick = (event) => {
    if (event && event.activePayload && event.activePayload.length > 0) {
      const point = event.activePayload[0].payload;
      if (point && point.target_start_time && onSelectTimestamp) {
        onSelectTimestamp(point.target_start_time);
      }
    }
  };

  if (!records || records.length === 0) {
    return (
      <div className="chart-card empty-chart-card">
        <h3>Forecast vs. Actual Wind Generation</h3>
        <p className="chart-empty-message">No timeseries observations available to display.</p>
      </div>
    );
  }

  return (
    <section className="chart-card" aria-labelledby="gen-chart-heading">
      <div className="chart-header">
        <div>
          <h2 id="gen-chart-heading" className="chart-title">
            Day-Ahead Wind Forecast vs. Actual Generation
          </h2>
          <p className="chart-subtitle">
            Hourly comparison of pre-cutoff day-ahead forecast against physical outturn.
            Missing periods are rendered as gaps without zero-filling.
          </p>
        </div>

        <div className="chart-controls">
          <div className="view-toggle-group">
            <button
              type="button"
              className={`btn-toggle ${visibleSlice === 'all' ? 'active' : ''}`}
              onClick={() => setVisibleSlice('all')}
            >
              Full Window ({records.length}h)
            </button>
            {records.length > 24 && (
              <button
                type="button"
                className={`btn-toggle ${visibleSlice === 'first-week' ? 'active' : ''}`}
                onClick={() => setVisibleSlice('first-week')}
              >
                First 7 Days
              </button>
            )}
            {records.length > 24 && (
              <button
                type="button"
                className={`btn-toggle ${visibleSlice === 'first-day' ? 'active' : ''}`}
                onClick={() => setVisibleSlice('first-day')}
              >
                24h Sample
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="chart-wrapper" style={{ width: '100%', height: 380 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 12, right: 24, left: 16, bottom: 20 }}
            onClick={handlePointClick}
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

            <Tooltip content={<CustomGenerationTooltip />} />

            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ paddingBottom: '12px' }}
            />

            {/* Day-Ahead Available Forecast (connectNulls=false to preserve gaps) */}
            <Line
              type="monotone"
              dataKey="forecast_generation_mw"
              name="Day-Ahead Forecast (Pre-Cutoff)"
              stroke="#00e5ff"
              strokeWidth={2}
              dot={chartData.length <= 48 ? { r: 3, fill: '#00e5ff' } : false}
              activeDot={{ r: 6, fill: '#00e5ff' }}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* Actual Wind Generation (connectNulls=false to preserve gaps) */}
            <Line
              type="monotone"
              dataKey="actual_generation_mw"
              name="Actual Generation Outturn"
              stroke="#00e676"
              strokeWidth={2}
              dot={chartData.length <= 48 ? { r: 3, fill: '#00e676' } : false}
              activeDot={{ r: 6, fill: '#00e676' }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer-caption">
        <span>
          💡 <strong>Analytical Note:</strong> The forecast series reflects the latest WINDFOR revision published prior to the configured cutoff on D-1.
          Click any data point or use the table below to inspect all forecast revisions published for that target hour.
        </span>
      </div>
    </section>
  );
}
