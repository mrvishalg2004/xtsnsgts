const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors with structured backend details.
 */
export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Internal helper to execute HTTP requests with structured error handling.
 */
async function apiFetch(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Accept': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `Server responded with status ${response.status} (${response.statusText})`;
      let errorDetail = null;

      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          errorDetail = errorData.detail;
          errorMessage = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // Response was not JSON
      }

      throw new ApiError(errorMessage, response.status, errorDetail);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw err; // Let caller handle aborts directly
    }
    if (err instanceof ApiError) {
      throw err;
    }
    // Network or connection error
    throw new ApiError(
      err.message || 'Unable to communicate with the analytics backend service. Ensure it is running.',
      0,
      null
    );
  }
}

/**
 * Checks the operational health of the FastAPI backend.
 *
 * @param {AbortSignal} [signal]
 * @returns {Promise<{ status: string, service: string, version: string, timestamp?: string }>}
 */
export async function checkHealth(signal) {
  const url = new URL('/api/health', API_BASE_URL);
  return apiFetch(url.toString(), { method: 'GET', signal });
}

/**
 * Retrieves aggregated statistical accuracy metrics and data-quality counts.
 *
 * @param {Object} filters
 * @param {string} filters.decision_start_date - YYYY-MM-DD
 * @param {string} filters.decision_end_date - YYYY-MM-DD
 * @param {string} filters.cutoff_time - HH:MM
 * @param {AbortSignal} [signal]
 * @returns {Promise<import('./types').SummaryMetricsResponse>}
 */
export async function fetchSummaryMetrics(filters, signal) {
  const url = new URL('/api/summary-metrics', API_BASE_URL);
  const params = new URLSearchParams();

  if (filters?.decision_start_date) {
    params.set('decision_start_date', filters.decision_start_date);
  }
  if (filters?.decision_end_date) {
    params.set('decision_end_date', filters.decision_end_date);
  }
  if (filters?.cutoff_time) {
    params.set('cutoff_time', filters.cutoff_time);
  }

  url.search = params.toString();
  return apiFetch(url.toString(), { method: 'GET', signal });
}

/**
 * Retrieves chronological hourly timeseries of day-ahead forecasts and actuals.
 *
 * @param {Object} filters
 * @param {string} filters.decision_start_date - YYYY-MM-DD
 * @param {string} filters.decision_end_date - YYYY-MM-DD
 * @param {string} filters.cutoff_time - HH:MM
 * @param {AbortSignal} [signal]
 * @returns {Promise<import('./types').TimeseriesResponse>}
 */
export async function fetchTimeseries(filters, signal) {
  const url = new URL('/api/timeseries', API_BASE_URL);
  const params = new URLSearchParams();

  if (filters?.decision_start_date) {
    params.set('decision_start_date', filters.decision_start_date);
  }
  if (filters?.decision_end_date) {
    params.set('decision_end_date', filters.decision_end_date);
  }
  if (filters?.cutoff_time) {
    params.set('cutoff_time', filters.cutoff_time);
  }

  url.search = params.toString();
  return apiFetch(url.toString(), { method: 'GET', signal });
}

/**
 * Inspects all historical WINDFOR publication runs for a specific target delivery hour.
 *
 * @param {string} targetStartTime - ISO-8601 UTC timestamp
 * @param {string} cutoffTime - HH:MM in UTC
 * @param {AbortSignal} [signal]
 * @returns {Promise<import('./types').RevisionsResponse>}
 */
export async function fetchRevisions(targetStartTime, cutoffTime = '09:50', signal) {
  const url = new URL('/api/revisions', API_BASE_URL);
  const params = new URLSearchParams();

  params.set('target_start_time', targetStartTime);
  if (cutoffTime) {
    params.set('cutoff_time', cutoffTime);
  }

  url.search = params.toString();
  return apiFetch(url.toString(), { method: 'GET', signal });
}

export { API_BASE_URL };
