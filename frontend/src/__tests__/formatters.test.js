import { describe, it, expect } from 'vitest';
import {
  formatMW,
  formatSignedMW,
  formatPercent,
  formatCount,
  formatUTCDateTime,
  formatUTCDate,
  formatUTCTime,
  getAvailabilityBadge,
  getRevisionStatusBadge,
} from '../utils/formatters';

describe('formatters utility unit tests', () => {
  it('formats MW values and returns em dash for null or undefined', () => {
    expect(formatMW(12345.67)).toBe('12,345.7');
    expect(formatMW(12345.67, 2, true)).toBe('12,345.67 MW');
    expect(formatMW(null)).toBe('—');
    expect(formatMW(undefined)).toBe('—');
    expect(formatMW(NaN)).toBe('—');
  });

  it('formats signed MW with explicit sign', () => {
    expect(formatSignedMW(3332.5)).toBe('+3,332.5');
    expect(formatSignedMW(-120.4)).toBe('-120.4');
    expect(formatSignedMW(0)).toBe('0.0');
    expect(formatSignedMW(null)).toBe('—');
    expect(formatSignedMW(undefined)).toBe('—');
  });

  it('formats percentage with percent symbol and handles nulls', () => {
    expect(formatPercent(21.07)).toBe('21.07%');
    expect(formatPercent(0)).toBe('0.00%');
    expect(formatPercent(null)).toBe('—');
    expect(formatPercent(undefined)).toBe('—');
  });

  it('formats integer counts', () => {
    expect(formatCount(24)).toBe('24');
    expect(formatCount(1488)).toBe('1,488');
    expect(formatCount(null)).toBe('0');
  });

  it('formats UTC date times correctly', () => {
    expect(formatUTCDateTime('2026-01-02T14:30:00Z')).toBe('2026-01-02 14:30 UTC');
    expect(formatUTCDateTime('2026-01-02T14:30:45Z', true)).toBe('2026-01-02 14:30:45 UTC');
    expect(formatUTCDateTime(null)).toBe('—');
    expect(formatUTCDate('2026-01-02T14:30:00Z')).toBe('2026-01-02');
    expect(formatUTCTime('2026-01-02T14:30:00Z')).toBe('14:30 UTC');
  });

  it('maps availability status to human-readable badges', () => {
    expect(getAvailabilityBadge('matched').label).toBe('Matched');
    expect(getAvailabilityBadge('missing_forecast').label).toBe('Missing Forecast');
    expect(getAvailabilityBadge('missing_actual').label).toBe('Missing Actual');
    expect(getAvailabilityBadge('missing_both').label).toBe('Missing Both');
  });

  it('maps revision status reasons to audit labels', () => {
    expect(getRevisionStatusBadge('selected').label).toBe('Selected Benchmark');
    expect(getRevisionStatusBadge('eligible_but_not_selected').label).toBe('Eligible (Superseded)');
    expect(getRevisionStatusBadge('published_after_cutoff').label).toBe('Excluded (Post-Cutoff)');
  });
});
