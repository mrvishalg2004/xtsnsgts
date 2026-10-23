import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';

// Polyfill ResizeObserver for JSDOM
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Recharts ResponsiveContainer needs dimensions in JSDOM
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ResponsiveContainer: ({ children, width = 800, height = 300 }) =>
      React.createElement(
        'div',
        { className: 'recharts-responsive-container', style: { width, height } },
        children
      ),
  };
});
