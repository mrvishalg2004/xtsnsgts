import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import App from '../App';
import * as api from '../services/api';

const mockSummaryData = {
  status: 'ok',
  filters: {
    decision_start_date: '2026-01-01',
    decision_end_date: '2026-01-31',
    cutoff_time: '09:50',
    delivery_start_date: '2026-01-02',
    delivery_end_date: '2026-02-01',
  },
  metrics: {
    mae: 3196.21,
    rmse: 3246.2,
    mbe: 3196.21,
    wape: 21.07,
    matched_count: 24,
    missing_actual_count: 0,
    missing_forecast_count: 0,
  },
  data_quality: {
    raw_fuelhh_count: 48,
    raw_windfor_count: 949,
    selected_forecast_count: 24,
    excluded_leakage_count: 24,
    hourly_actual_count: 24,
    matched_count: 24,
    missing_actual_count: 0,
    missing_forecast_count: 0,
    missing_both_count: 0,
  },
  cache_metadata: {
    cached: true,
    data_retrieval_timestamp: '2026-10-23T15:29:40.123456Z',
    cache_ttl_seconds: 900,
  },
};

const mockTimeseriesData = {
  status: 'ok',
  filters: {
    decision_start_date: '2026-01-01',
    decision_end_date: '2026-01-31',
    cutoff_time: '09:50',
    delivery_start_date: '2026-01-02',
    delivery_end_date: '2026-02-01',
  },
  total_periods: 3,
  records: [
    {
      target_start_time: '2026-01-02T00:00:00Z',
      delivery_date: '2026-01-02',
      decision_date: '2026-01-01',
      decision_cutoff: '2026-01-01T09:50:00Z',
      forecast_publish_time: '2026-01-01T08:30:00Z',
      forecast_generation_mw: 18699.0,
      actual_generation_mw: 15366.5,
      error_mw: 3332.5,
      absolute_error_mw: 3332.5,
      availability_status: 'matched',
    },
    {
      target_start_time: '2026-01-02T01:00:00Z',
      delivery_date: '2026-01-02',
      decision_date: '2026-01-01',
      decision_cutoff: '2026-01-01T09:50:00Z',
      forecast_publish_time: '2026-01-01T08:30:00Z',
      forecast_generation_mw: 17200.0,
      actual_generation_mw: 17500.0,
      error_mw: -300.0,
      absolute_error_mw: 300.0,
      availability_status: 'matched',
    },
    {
      target_start_time: '2026-01-02T02:00:00Z',
      delivery_date: '2026-01-02',
      decision_date: '2026-01-01',
      decision_cutoff: '2026-01-01T09:50:00Z',
      forecast_publish_time: null,
      forecast_generation_mw: null,
      actual_generation_mw: 16000.0,
      error_mw: null,
      absolute_error_mw: null,
      availability_status: 'missing_forecast',
    },
  ],
  cache_metadata: {
    cached: true,
    data_retrieval_timestamp: '2026-10-23T15:29:40.123456Z',
    cache_ttl_seconds: 900,
  },
};

const mockRevisionsData = {
  status: 'ok',
  target_start_time: '2026-01-02T00:00:00Z',
  delivery_date: '2026-01-02',
  decision_date: '2026-01-01',
  decision_cutoff: '2026-01-01T09:50:00Z',
  total_revisions: 3,
  eligible_revisions_count: 2,
  selected_revision: {
    publish_time: '2026-01-01T08:30:00Z',
    forecast_generation_mw: 18699.0,
    is_eligible: true,
    is_selected: true,
    status_reason: 'selected',
  },
  revisions: [
    {
      publish_time: '2026-01-01T05:00:00Z',
      forecast_generation_mw: 18200.0,
      is_eligible: true,
      is_selected: false,
      status_reason: 'eligible_but_not_selected',
    },
    {
      publish_time: '2026-01-01T08:30:00Z',
      forecast_generation_mw: 18699.0,
      is_eligible: true,
      is_selected: true,
      status_reason: 'selected',
    },
    {
      publish_time: '2026-01-01T12:00:00Z',
      forecast_generation_mw: 19000.0,
      is_eligible: false,
      is_selected: false,
      status_reason: 'published_after_cutoff',
    },
  ],
  cache_metadata: {
    cached: true,
    data_retrieval_timestamp: '2026-10-23T15:29:40.123456Z',
    cache_ttl_seconds: 900,
  },
};

describe('Wind Forecast Analytics Dashboard Component Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, 'checkHealth').mockResolvedValue({ status: 'ok', service: 'wind_forecast_insights' });
    vi.spyOn(api, 'fetchSummaryMetrics').mockResolvedValue(mockSummaryData);
    vi.spyOn(api, 'fetchTimeseries').mockResolvedValue(mockTimeseriesData);
    vi.spyOn(api, 'fetchRevisions').mockResolvedValue(mockRevisionsData);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial loading state and then populates dashboard with KPI metrics', async () => {
    render(<App />);

    // Initially displays brand title
    expect(screen.getByText(/wind forecast insights/i)).toBeInTheDocument();

    // Waits for analysis data to load
    await waitFor(() => {
      expect(screen.getByText('Key Forecast Accuracy Indicators')).toBeInTheDocument();
    });

    // Verifies KPI values rendered from API
    // MAE: 3,196.2 MW
    const maeCard = document.getElementById('kpi-mae');
    expect(maeCard).toBeInTheDocument();
    expect(within(maeCard).getByText('3,196.2')).toBeInTheDocument();

    // RMSE: 3,246.2 MW
    const rmseCard = document.getElementById('kpi-rmse');
    expect(rmseCard).toBeInTheDocument();
    expect(within(rmseCard).getByText('3,246.2')).toBeInTheDocument();

    // MBE: +3,196.2 MW (over-forecast bias)
    const mbeCard = document.getElementById('kpi-mbe');
    expect(mbeCard).toBeInTheDocument();
    expect(within(mbeCard).getByText('+3,196.2')).toBeInTheDocument();
    expect(within(mbeCard).getByText('Over-Forecast Bias')).toBeInTheDocument();

    // WAPE: 21.07%
    const wapeCard = document.getElementById('kpi-wape');
    expect(wapeCard).toBeInTheDocument();
    expect(within(wapeCard).getByText('21.07%')).toBeInTheDocument();

    // Matched Hours: 24
    const matchedCard = document.getElementById('kpi-matched-count');
    expect(matchedCard).toBeInTheDocument();
    expect(within(matchedCard).getByText('24')).toBeInTheDocument();
  });

  it('renders null metrics as unavailable em dash (—) and not as zero', async () => {
    const nullMetricsSummary = {
      ...mockSummaryData,
      metrics: {
        mae: null,
        rmse: null,
        mbe: null,
        wape: null,
        matched_count: 0,
        missing_actual_count: 10,
        missing_forecast_count: 10,
      },
    };

    api.fetchSummaryMetrics.mockResolvedValue(nullMetricsSummary);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Key Forecast Accuracy Indicators')).toBeInTheDocument();
    });

    const maeCard = document.getElementById('kpi-mae');
    expect(within(maeCard).getByText('—')).toBeInTheDocument();
    expect(within(maeCard).queryByText('0.0')).not.toBeInTheDocument();

    const wapeCard = document.getElementById('kpi-wape');
    expect(within(wapeCard).getByText('—')).toBeInTheDocument();
    expect(within(wapeCard).queryByText('0.00%')).not.toBeInTheDocument();
  });

  it('renders backend error state when API request fails', async () => {
    api.fetchSummaryMetrics.mockRejectedValue(new Error('Connection refused'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Forecast Evaluation Error')).toBeInTheDocument();
      expect(screen.getByText('Connection refused')).toBeInTheDocument();
    });
  });

  it('submitting filters sends the correct query parameters', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Key Forecast Accuracy Indicators')).toBeInTheDocument();
    });

    const startInput = screen.getByLabelText(/decision start date/i);
    const endInput = screen.getByLabelText(/decision end date/i);
    const cutoffInput = screen.getByLabelText(/decision cutoff time/i);
    const applyButton = screen.getByRole('button', { name: /apply parameters|run analysis/i });

    // Change parameters
    fireEvent.change(startInput, { target: { value: '2026-01-05' } });
    fireEvent.change(endInput, { target: { value: '2026-01-10' } });
    fireEvent.change(cutoffInput, { target: { value: '11:00' } });

    fireEvent.click(applyButton);

    await waitFor(() => {
      expect(api.fetchSummaryMetrics).toHaveBeenCalledWith(
        expect.objectContaining({
          decision_start_date: '2026-01-05',
          decision_end_date: '2026-01-10',
          cutoff_time: '11:00',
        }),
        expect.any(AbortSignal)
      );
    });
  });

  it('preserves missing values as em dashes in the ledger table without zero-filling', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Hourly Timeseries Ledger')).toBeInTheDocument();
    });

    // The third record (2026-01-02 02:00 UTC) has missing forecast
    const table = screen.getByRole('table', { name: /hourly wind forecast/i });
    const missingForecastBadge = within(table).getByText('Missing Forecast');
    expect(missingForecastBadge).toBeInTheDocument();

    // Verify row contains em dash for forecast and signed error
    const row = missingForecastBadge.closest('tr');
    expect(row).toBeInTheDocument();
    const cells = within(row).getAllByText('—');
    expect(cells.length).toBeGreaterThanOrEqual(2); // Forecast and Error are '—'
  });

  it('distinguishes positive over-forecast error from negative under-forecast error', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Hourly Timeseries Ledger')).toBeInTheDocument();
    });

    // Record 1: +3,332.5 MW (over-forecast)
    expect(screen.getByText('+3,332.5')).toBeInTheDocument();

    // Record 2: -300.0 MW (under-forecast)
    expect(screen.getByText('-300.0')).toBeInTheDocument();
  });

  it('opens revision inspector modal and renders selected benchmark vs excluded revisions', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Hourly Timeseries Ledger')).toBeInTheDocument();
    });

    // Find and click the first "Inspect" button
    const inspectButtons = screen.getAllByRole('button', { name: /inspect/i });
    expect(inspectButtons.length).toBeGreaterThan(0);
    fireEvent.click(inspectButtons[0]);

    // Modal should open
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Forecast Revision History')).toBeInTheDocument();
    });

    // Verifies fetchRevisions was called
    expect(api.fetchRevisions).toHaveBeenCalledWith(
      '2026-01-02T00:00:00Z',
      '09:50'
    );

    // Selected benchmark displayed
    expect(screen.getByText('⭐ Selected Day-Ahead Benchmark')).toBeInTheDocument();
    expect(screen.getByText('18,699.0 MW')).toBeInTheDocument();

    // Table of revisions with status reasons
    expect(screen.getByText('Eligible (Superseded)')).toBeInTheDocument();
    expect(screen.getAllByText('Excluded (Post-Cutoff)').length).toBeGreaterThanOrEqual(1);

    // Close modal
    const closeButton = screen.getByRole('button', { name: /close revision inspector/i });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('prevents stale requests from replacing newer applied analysis results', async () => {
    let resolveFirst;
    const slowFirstPromise = new Promise((resolve) => {
      resolveFirst = resolve;
    });

    api.fetchSummaryMetrics
      .mockImplementationOnce(() => slowFirstPromise)
      .mockResolvedValueOnce({
        ...mockSummaryData,
        metrics: { ...mockSummaryData.metrics, mae: 9999.0 },
      });

    render(<App />);

    // Fast second request triggered by filter change
    const startInput = screen.getByLabelText(/decision start date/i);
    fireEvent.change(startInput, { target: { value: '2026-01-15' } });
    const applyButton = screen.getByRole('button', { name: /apply parameters/i });
    fireEvent.click(applyButton);

    // Second request resolves first
    await waitFor(() => {
      const maeCard = document.getElementById('kpi-mae');
      if (maeCard) {
        expect(within(maeCard).getByText('9,999.0')).toBeInTheDocument();
      }
    });

    // Now resolve the old stale request
    resolveFirst(mockSummaryData);

    // The display must NOT be overwritten with the old MAE 3,196.2
    const maeCard = document.getElementById('kpi-mae');
    expect(within(maeCard).getByText('9,999.0')).toBeInTheDocument();
  });
});



