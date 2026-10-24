import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react';
import {
  checkHealth,
  fetchSummaryMetrics,
  fetchTimeseries,
  fetchRevisions,
} from './services/api';

import AppHeader from './components/AppHeader';
import AnalysisFilters from './components/AnalysisFilters';
import KpiMetricsGrid from './components/MetricCard';
import GenerationChart from './components/GenerationChart';
import ForecastErrorChart from './components/ForecastErrorChart';
import DataQualityPanel from './components/DataQualityPanel';
import TimeseriesTable from './components/TimeseriesTable';
import LoadingState from './components/LoadingState';
import ErrorState from './components/ErrorState';
import EmptyState from './components/EmptyState';

const RevisionInspector = lazy(() => import('./components/RevisionInspector'));

const DEFAULT_FILTERS = {
  decision_start_date: '2026-01-01',
  decision_end_date: '2026-01-31',
  cutoff_time: '09:50',
};

export default function App() {
  // Backend connectivity status
  const [healthStatus, setHealthStatus] = useState('loading'); // 'loading' | 'available' | 'unavailable'

  // Applied evaluation filters
  const [appliedFilters, setAppliedFilters] = useState(DEFAULT_FILTERS);

  // Analysis data state
  const [summaryData, setSummaryData] = useState(null);
  const [timeseriesData, setTimeseriesData] = useState(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(true);
  const [analysisError, setAnalysisError] = useState(null);
  const [refreshError, setRefreshError] = useState(null);

  // Revision Inspector state
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [selectedTimestamp, setSelectedTimestamp] = useState(null);
  const [revisionsData, setRevisionsData] = useState(null);
  const [isLoadingRevisions, setIsLoadingRevisions] = useState(false);
  const [revisionsError, setRevisionsError] = useState(null);

  // Deduplication cache for revision inspection: key `${timestamp}_${cutoff}` -> data
  const revisionsCacheRef = useRef(new Map());

  // Request race-condition management
  const activeAbortControllerRef = useRef(null);
  const latestRequestIdRef = useRef(0);
  const summaryDataRef = useRef(null);

  useEffect(() => {
    summaryDataRef.current = summaryData;
  }, [summaryData]);

  /**
   * Check backend health
   */
  const handleCheckHealth = useCallback(async () => {
    setHealthStatus('loading');
    try {
      await checkHealth();
      setHealthStatus('available');
    } catch {
      setHealthStatus('unavailable');
    }
  }, []);

  /**
   * Load summary metrics and timeseries data for the applied filters.
   * Cancels any in-flight request to prevent race conditions.
   */
  const loadAnalysis = useCallback(async (filters, isRefresh = false) => {
    // Cancel any prior in-flight request
    if (activeAbortControllerRef.current) {
      activeAbortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    activeAbortControllerRef.current = abortController;
    const currentRequestId = ++latestRequestIdRef.current;

    if (!isRefresh) {
      setIsLoadingAnalysis(true);
      setAnalysisError(null);
    }
    setRefreshError(null);

    try {
      const [summaryRes, timeseriesRes] = await Promise.all([
        fetchSummaryMetrics(filters, abortController.signal),
        fetchTimeseries(filters, abortController.signal),
      ]);

      // If a newer request has already started, discard this result
      if (currentRequestId !== latestRequestIdRef.current) {
        return;
      }

      setSummaryData(summaryRes);
      setTimeseriesData(timeseriesRes);
      setAnalysisError(null);
      setRefreshError(null);
    } catch (err) {
      if (err.name === 'AbortError') {
        // Request was cancelled intentionally by a newer action
        return;
      }

      if (currentRequestId !== latestRequestIdRef.current) {
        return;
      }

      if (isRefresh && summaryDataRef.current) {
        // Retain previous successful analysis, but clearly mark the refresh error
        setRefreshError(err.message || 'Refresh failed. Retaining previously loaded analysis.');
      } else {
        setAnalysisError(err);
      }
    } finally {
      if (currentRequestId === latestRequestIdRef.current) {
        setIsLoadingAnalysis(false);
      }
    }
  }, []);

  /**
   * Initial mount: verify health and load default January analysis
   */
  useEffect(() => {
    handleCheckHealth();
    loadAnalysis(DEFAULT_FILTERS);

    return () => {
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }
    };
  }, [handleCheckHealth, loadAnalysis]);

  /**
   * Handle user applying new filters from the filter control panel
   */
  const handleApplyFilters = (newFilters) => {
    setAppliedFilters(newFilters);
    // Clear revisions cache when cutoff changes
    revisionsCacheRef.current.clear();
    loadAnalysis(newFilters, false);
  };

  /**
   * Handle explicit user refresh
   */
  const handleRefresh = () => {
    loadAnalysis(appliedFilters, true);
  };

  /**
   * Handle user selecting a delivery period to inspect forecast publication revisions
   */
  const handleInspectRevision = async (targetStartTime) => {
    if (!targetStartTime) return;

    setSelectedTimestamp(targetStartTime);
    setIsInspectorOpen(true);
    setRevisionsError(null);

    const cacheKey = `${targetStartTime}_${appliedFilters.cutoff_time}`;
    if (revisionsCacheRef.current.has(cacheKey)) {
      setRevisionsData(revisionsCacheRef.current.get(cacheKey));
      setIsLoadingRevisions(false);
      return;
    }

    setIsLoadingRevisions(true);
    setRevisionsData(null);

    try {
      const data = await fetchRevisions(targetStartTime, appliedFilters.cutoff_time);
      revisionsCacheRef.current.set(cacheKey, data);
      setRevisionsData(data);
    } catch (err) {
      setRevisionsError(err.message || 'Unable to retrieve forecast revisions');
    } finally {
      setIsLoadingRevisions(false);
    }
  };

  const handleCloseInspector = () => {
    setIsInspectorOpen(false);
  };

  // Derive active cache metadata from response
  const activeCacheMetadata = summaryData?.cache_metadata || timeseriesData?.cache_metadata;
  const timeseriesRecords = timeseriesData?.records || [];
  const metrics = summaryData?.metrics;
  const dataQuality = summaryData?.data_quality;

  // Determine if result is completely empty
  const isEmptyResult =
    !isLoadingAnalysis &&
    !analysisError &&
    summaryData &&
    timeseriesRecords.length === 0;

  return (
    <div className="app-container">
      {/* 1. App Header */}
      <AppHeader
        healthStatus={healthStatus}
        onCheckHealth={handleCheckHealth}
        cacheMetadata={activeCacheMetadata}
        configuredCutoff={appliedFilters.cutoff_time}
      />

      <main className="app-main">
        {/* 2. Decision Parameters Filter Panel */}
        <AnalysisFilters
          appliedFilters={appliedFilters}
          onApplyFilters={handleApplyFilters}
          onRefresh={handleRefresh}
          isLoading={isLoadingAnalysis}
        />

        {/* Transient Refresh Error Banner (if refreshing fails but previous data remains) */}
        {refreshError && (
          <div className="transient-error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <div className="transient-error-content">
              <strong>Refresh Failed:</strong> {refreshError}
              <span className="transient-error-note">
                Displaying previous analysis. Data may not reflect recent backend updates.
              </span>
            </div>
            <button
              type="button"
              className="btn-dismiss"
              onClick={() => setRefreshError(null)}
              aria-label="Dismiss banner"
            >
              ✕
            </button>
          </div>
        )}

        {/* 3. Main Analysis Content Area */}
        {isLoadingAnalysis ? (
          <LoadingState
            title="Evaluating Wind Forecasts..."
            message={`Processing decision window ${appliedFilters.decision_start_date} to ${appliedFilters.decision_end_date} at ${appliedFilters.cutoff_time} UTC cutoff.`}
          />
        ) : analysisError ? (
          <ErrorState
            title="Forecast Evaluation Error"
            error={analysisError}
            onRetry={() => loadAnalysis(appliedFilters, false)}
          />
        ) : isEmptyResult ? (
          <EmptyState
            title="No Paired Wind Observations Found"
            message={`No matched intervals found for decision dates ${appliedFilters.decision_start_date} to ${appliedFilters.decision_end_date} with cutoff ${appliedFilters.cutoff_time} UTC.`}
            onReset={() => handleApplyFilters(DEFAULT_FILTERS)}
          />
        ) : (
          <>
            {/* KPI Summary Cards */}
            <KpiMetricsGrid metrics={metrics} dataQuality={dataQuality} />

            {/* Time-Series Generation Chart */}
            <GenerationChart
              records={timeseriesRecords}
              onSelectTimestamp={handleInspectRevision}
              selectedTimestamp={selectedTimestamp}
            />

            {/* Signed Forecast Error (Residuals) Chart */}
            <ForecastErrorChart records={timeseriesRecords} />

            {/* Data Quality & Pipeline Reconciliation Audit */}
            <DataQualityPanel dataQuality={dataQuality} />

            {/* Detailed Hourly Timeseries Ledger */}
            <TimeseriesTable
              records={timeseriesRecords}
              onInspectRevision={handleInspectRevision}
              selectedTimestamp={selectedTimestamp}
            />
          </>
        )}
      </main>

      {/* 4. Forecast Revision Audit Inspector Modal */}
      {isInspectorOpen && (
        <Suspense fallback={null}>
          <RevisionInspector
            isOpen={isInspectorOpen}
            onClose={handleCloseInspector}
            targetStartTime={selectedTimestamp}
            cutoffTime={appliedFilters.cutoff_time}
            data={revisionsData}
            isLoading={isLoadingRevisions}
            error={revisionsError}
          />
        </Suspense>
      )}

      {/* 5. Accessible Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p>
            Official Elexon Insights Solution Datasets:{' '}
            <a
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
              target="_blank"
              rel="noreferrer"
            >
              FUELHH (WIND)
            </a>{' '}
            &amp;{' '}
            <a
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
              target="_blank"
              rel="noreferrer"
            >
              WINDFOR
            </a>
            . Sample N2EX 09:50 UTC decision cutoff assumption for UK Day-Ahead power purchasing in January 2026.
          </p>
          <p className="footer-subtext">
            Strict anti-leakage forecast selection protocol. Missing observations are excluded from paired accuracy indicators without zero-imputation.
          </p>
        </div>
      </footer>
    </div>
  );
}
