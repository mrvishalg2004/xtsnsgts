/**
 * Data and timestamp formatting utilities for Wind Forecast Insights.
 * Consistent presentation helpers that never alter underlying analytical data.
 */

/**
 * Format a numeric power value in Megawatts (MW).
 * Returns an em dash ('—') for null or non-finite values.
 *
 * @param {number|null|undefined} val - Value in MW
 * @param {number} decimals - Number of decimal places (default 1)
 * @param {boolean} includeUnit - Whether to append ' MW' (default false)
 * @returns {string} Formatted string
 */
export function formatMW(val, decimals = 1, includeUnit = false) {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  const formatted = Number(val).toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return includeUnit ? `${formatted} MW` : formatted;
}

/**
 * Format a signed forecast error in Megawatts (MW) with explicit '+' or '-' sign.
 * Returns an em dash ('—') for null or non-finite values.
 *
 * @param {number|null|undefined} val - Signed error in MW
 * @param {number} decimals - Number of decimal places (default 1)
 * @param {boolean} includeUnit - Whether to append ' MW' (default false)
 * @returns {string} Formatted string with sign
 */
export function formatSignedMW(val, decimals = 1, includeUnit = false) {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  const num = Number(val);
  const sign = num > 0 ? '+' : '';
  const formatted = `${sign}${num.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
  return includeUnit ? `${formatted} MW` : formatted;
}

/**
 * Format an error percentage (e.g. WAPE).
 * Returns an em dash ('—') for null or non-finite values.
 *
 * @param {number|null|undefined} val - Percentage value
 * @param {number} decimals - Decimal places (default 2)
 * @returns {string} Formatted string with '%'
 */
export function formatPercent(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  return `${Number(val).toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}

/**
 * Format integer record counts.
 *
 * @param {number|null|undefined} val - Count value
 * @returns {string} Formatted count
 */
export function formatCount(val) {
  if (val === null || val === undefined || isNaN(val)) {
    return '0';
  }
  return Math.round(Number(val)).toLocaleString('en-GB');
}

/**
 * Format an ISO-8601 UTC timestamp into a legible UTC string.
 * e.g. "2026-01-02T14:00:00Z" -> "2026-01-02 14:00 UTC"
 *
 * @param {string|Date|null|undefined} isoString - ISO datetime string
 * @param {boolean} includeSeconds - Whether to show seconds
 * @returns {string} Formatted UTC string
 */
export function formatUTCDateTime(isoString, includeSeconds = false) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    const year = d.getUTCFullYear();
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    const hours = String(d.getUTCHours()).padStart(2, '0');
    const minutes = String(d.getUTCMinutes()).padStart(2, '0');
    if (includeSeconds) {
      const seconds = String(d.getUTCSeconds()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
    }
    return `${year}-${month}-${day} ${hours}:${minutes} UTC`;
  } catch {
    return '—';
  }
}

/**
 * Format an ISO string to UTC date only: "YYYY-MM-DD".
 *
 * @param {string|Date|null|undefined} isoString
 * @returns {string} Formatted date
 */
export function formatUTCDate(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    const year = d.getUTCFullYear();
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch {
    return '—';
  }
}

/**
 * Format an ISO string to UTC time only: "HH:MM UTC".
 *
 * @param {string|Date|null|undefined} isoString
 * @returns {string} Formatted time
 */
export function formatUTCTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    const hours = String(d.getUTCHours()).padStart(2, '0');
    const minutes = String(d.getUTCMinutes()).padStart(2, '0');
    return `${hours}:${minutes} UTC`;
  } catch {
    return '—';
  }
}

/**
 * Map API availability status codes to user-friendly badge configurations.
 *
 * @param {string} status - 'matched' | 'missing_forecast' | 'missing_actual' | 'missing_both'
 * @returns {{ label: string, className: string, description: string }}
 */
export function getAvailabilityBadge(status) {
  switch (status) {
    case 'matched':
      return {
        label: 'Matched',
        className: 'badge-status-matched',
        description: 'Both eligible forecast and complete actual generation present',
      };
    case 'missing_forecast':
      return {
        label: 'Missing Forecast',
        className: 'badge-status-missing-forecast',
        description: 'No eligible forecast published before decision cutoff',
      };
    case 'missing_actual':
      return {
        label: 'Missing Actual',
        className: 'badge-status-missing-actual',
        description: 'Actual generation outturn missing or incomplete for period',
      };
    case 'missing_both':
      return {
        label: 'Missing Both',
        className: 'badge-status-missing-both',
        description: 'Neither eligible forecast nor actual generation available',
      };
    default:
      return {
        label: status || 'Unknown',
        className: 'badge-status-unknown',
        description: 'Status unknown',
      };
  }
}

/**
 * Map revision status_reason to human-readable labels and badge styles.
 *
 * @param {string} reason - 'selected' | 'eligible_but_not_selected' | 'published_after_cutoff'
 * @returns {{ label: string, className: string, description: string }}
 */
export function getRevisionStatusBadge(reason) {
  switch (reason) {
    case 'selected':
      return {
        label: 'Selected Benchmark',
        className: 'revision-badge-selected',
        description: 'Latest eligible revision published before decision cutoff — used in evaluation',
      };
    case 'eligible_but_not_selected':
      return {
        label: 'Eligible (Superseded)',
        className: 'revision-badge-eligible',
        description: 'Published before cutoff, but superseded by a later pre-cutoff revision',
      };
    case 'published_after_cutoff':
      return {
        label: 'Excluded (Post-Cutoff)',
        className: 'revision-badge-excluded',
        description: 'Published after decision cutoff — excluded to strictly prevent future-data leakage',
      };
    default:
      return {
        label: reason || 'Unknown',
        className: 'revision-badge-unknown',
        description: '',
      };
  }
}
