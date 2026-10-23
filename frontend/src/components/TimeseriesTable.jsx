import { useState, useMemo } from 'react';
import {
  formatMW,
  formatSignedMW,
  formatUTCDateTime,
  getAvailabilityBadge,
} from '../utils/formatters';

export default function TimeseriesTable({
  records = [],
  onInspectRevision,
  selectedTimestamp = null,
}) {
  const [pageSize, setPageSize] = useState(24);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState('target_start_time');
  const [sortDirection, setSortDirection] = useState('asc');
  const [statusFilter, setStatusFilter] = useState('all');

  // Filter records
  const filteredRecords = useMemo(() => {
    if (!records) return [];
    if (statusFilter === 'all') return records;
    return records.filter((r) => r.availability_status === statusFilter);
  }, [records, statusFilter]);

  // Sort records
  const sortedRecords = useMemo(() => {
    return [...filteredRecords].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      // Handle nulls: put nulls at the end
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === 'string') {
        const cmp = valA.localeCompare(valB);
        return sortDirection === 'asc' ? cmp : -cmp;
      }

      const diff = Number(valA) - Number(valB);
      return sortDirection === 'asc' ? diff : -diff;
    });
  }, [filteredRecords, sortField, sortDirection]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sortedRecords.length / pageSize));
  const pageStart = (currentPage - 1) * pageSize;
  const paginatedRecords = sortedRecords.slice(pageStart, pageStart + pageSize);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  const renderSortIndicator = (field) => {
    if (sortField !== field) return <span className="sort-indicator neutral">↕</span>;
    return <span className="sort-indicator active">{sortDirection === 'asc' ? '▲' : '▼'}</span>;
  };

  return (
    <section className="table-card" aria-labelledby="table-heading">
      <div className="table-card-header">
        <div>
          <h2 id="table-heading" className="table-title">
            Hourly Timeseries Ledger
          </h2>
          <p className="table-subtitle">
            Target delivery hours showing pre-cutoff forecasts, physical outturns, and residual deviations.
          </p>
        </div>

        <div className="table-controls-row">
          <div className="filter-group-inline">
            <label htmlFor="status-filter-select" className="inline-label">
              Status Filter:
            </label>
            <select
              id="status-filter-select"
              className="select-input"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="all">All Hours ({records.length})</option>
              <option value="matched">Matched Only</option>
              <option value="missing_forecast">Missing Forecast</option>
              <option value="missing_actual">Missing Actual</option>
              <option value="missing_both">Missing Both</option>
            </select>
          </div>

          <div className="filter-group-inline">
            <label htmlFor="page-size-select" className="inline-label">
              Rows:
            </label>
            <select
              id="page-size-select"
              className="select-input"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
            >
              <option value={24}>24 (1 Day)</option>
              <option value={48}>48 (2 Days)</option>
              <option value={168}>168 (1 Week)</option>
              <option value={744}>All Hours</option>
            </select>
          </div>
        </div>
      </div>

      <div className="table-responsive-container">
        <table className="timeseries-table" aria-label="Hourly wind forecast and actual generation ledger">
          <thead>
            <tr>
              <th scope="col" onClick={() => handleSort('target_start_time')} className="sortable-th">
                Delivery Target (UTC) {renderSortIndicator('target_start_time')}
              </th>
              <th scope="col" onClick={() => handleSort('delivery_date')} className="sortable-th">
                Delivery Day {renderSortIndicator('delivery_date')}
              </th>
              <th scope="col" onClick={() => handleSort('decision_date')} className="sortable-th">
                Decision Day {renderSortIndicator('decision_date')}
              </th>
              <th scope="col" onClick={() => handleSort('forecast_publish_time')} className="sortable-th">
                Forecast Published {renderSortIndicator('forecast_publish_time')}
              </th>
              <th scope="col" onClick={() => handleSort('forecast_generation_mw')} className="sortable-th num-col">
                Forecast (MW) {renderSortIndicator('forecast_generation_mw')}
              </th>
              <th scope="col" onClick={() => handleSort('actual_generation_mw')} className="sortable-th num-col">
                Actual (MW) {renderSortIndicator('actual_generation_mw')}
              </th>
              <th scope="col" onClick={() => handleSort('error_mw')} className="sortable-th num-col">
                Signed Error (MW) {renderSortIndicator('error_mw')}
              </th>
              <th scope="col" onClick={() => handleSort('absolute_error_mw')} className="sortable-th num-col">
                |Error| (MW) {renderSortIndicator('absolute_error_mw')}
              </th>
              <th scope="col" onClick={() => handleSort('availability_status')} className="sortable-th">
                Status {renderSortIndicator('availability_status')}
              </th>
              <th scope="col" className="action-col">
                Audit
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedRecords.length === 0 ? (
              <tr>
                <td colSpan={10} className="empty-table-cell">
                  No records match the selected filter parameters.
                </td>
              </tr>
            ) : (
              paginatedRecords.map((record) => {
                const badge = getAvailabilityBadge(record.availability_status);
                const isSelected = selectedTimestamp === record.target_start_time;
                const isPositive = record.error_mw !== null && record.error_mw > 0;
                const isNegative = record.error_mw !== null && record.error_mw < 0;

                return (
                  <tr
                    key={record.target_start_time}
                    className={`table-row ${isSelected ? 'row-selected' : ''}`}
                  >
                    <td className="cell-timestamp font-mono">
                      {formatUTCDateTime(record.target_start_time)}
                    </td>
                    <td>{record.delivery_date}</td>
                    <td>{record.decision_date}</td>
                    <td className="font-mono text-muted">
                      {formatUTCDateTime(record.forecast_publish_time)}
                    </td>
                    <td className="num-col font-mono">
                      {formatMW(record.forecast_generation_mw, 1)}
                    </td>
                    <td className="num-col font-mono">
                      {formatMW(record.actual_generation_mw, 1)}
                    </td>
                    <td
                      className={`num-col font-mono ${
                        isPositive ? 'cell-positive' : isNegative ? 'cell-negative' : ''
                      }`}
                    >
                      {formatSignedMW(record.error_mw, 1)}
                    </td>
                    <td className="num-col font-mono text-muted">
                      {formatMW(record.absolute_error_mw, 1)}
                    </td>
                    <td>
                      <span className={`table-badge ${badge.className}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="action-col">
                      <button
                        type="button"
                        className="btn-inspect"
                        onClick={() => onInspectRevision(record.target_start_time)}
                        title={`Inspect all WINDFOR publications for ${record.target_start_time}`}
                        aria-label={`Inspect revisions for ${record.target_start_time}`}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="table-pagination-footer">
        <span className="pagination-summary">
          Showing {sortedRecords.length === 0 ? 0 : pageStart + 1}–
          {Math.min(pageStart + pageSize, sortedRecords.length)} of {sortedRecords.length} hours
        </span>

        <div className="pagination-buttons">
          <button
            type="button"
            className="btn-page"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage(1)}
            title="First page"
          >
            «
          </button>
          <button
            type="button"
            className="btn-page"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            title="Previous page"
          >
            ‹ Prev
          </button>
          <span className="page-indicator">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="btn-page"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            title="Next page"
          >
            Next ›
          </button>
          <button
            type="button"
            className="btn-page"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage(totalPages)}
            title="Last page"
          >
            »
          </button>
        </div>
      </div>
    </section>
  );
}
