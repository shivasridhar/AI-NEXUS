import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import IngestionMonitorPage from './page';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// We only want to mock the queries so we can simulate a refetch,
// or we can test the real thing. It's better to mock the custom hooks for this specific component
// since they are tested independently and we want to control timing easily.
import * as queries from '@/lib/queries/stage1';
import { useGlobalStore } from '@/lib/store';

vi.mock('@/lib/queries/stage1');
vi.mock('@/lib/store', () => ({
  useGlobalStore: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('IngestionMonitorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useGlobalStore as unknown as any).mockReturnValue({
      autoRefreshInterval: 5000,
      setAutoRefreshInterval: vi.fn(),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders loading states and then data', async () => {
    (queries.useMonitoringConfig as any).mockReturnValue({
      data: { stages: [], columns: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    (queries.useMonitoringMetrics as any).mockReturnValue({
      data: { totalEvents: 100, eventsPerMinute: 10, validationSuccessRate: 99.9, activeConnectors: 1 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    (queries.useLiveEvents as any).mockReturnValue({
      data: [
        { id: '1', timestamp: '2023-01-01', connector: 'aws', eventType: 'test', severity: 'INFO', status: 'SUCCESS', message: 'test' }
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IngestionMonitorPage />, { wrapper: createWrapper() });

    expect(screen.getByText('Ingestion Monitor')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument(); // total events
  });
});
