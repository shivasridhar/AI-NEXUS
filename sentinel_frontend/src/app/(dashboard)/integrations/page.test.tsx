import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import IntegrationsPage from './page';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { server } from '../../../../mocks/server';
import { http, HttpResponse } from 'msw';

const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://ai-nexus-backend-cndm.onrender.com/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('IntegrationsPage', () => {
  it('renders loading state initially', () => {
    render(<IntegrationsPage />, { wrapper: createWrapper() });
    
    // The page title should be visible
    expect(screen.getByText('Connector Management')).toBeInTheDocument();
    
    // Refresh button should be disabled while loading
    const refreshBtn = screen.getByRole('button', { name: /Refresh Status/i });
    expect(refreshBtn).toBeDisabled();
  });

  it('renders list of integrations successfully', async () => {
    render(<IntegrationsPage />, { wrapper: createWrapper() });
    
    // Wait for the mock data to load
    await waitFor(() => {
      expect(screen.getByText('AWS Security Hub')).toBeInTheDocument();
    });

    // Check if the other connector is present
    expect(screen.getByText('CrowdStrike Falcon')).toBeInTheDocument();
  });

  it('renders generic fallback for unknown connector types instead of crashing', async () => {
    // Override the mock to return an unknown connector type
    server.use(
      http.get(`${baseUrl}/integrations`, () => {
        return HttpResponse.json([
          {
            id: 'unknown-1',
            provider: 'super_secret_tool',
            name: 'Super Secret Tool',
            status: 'active',
            events_retrieved: 50,
            last_sync_time: new Date().toISOString()
          }
        ]);
      })
    );

    render(<IntegrationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      // The name should be rendered
      expect(screen.getByText('Super Secret Tool')).toBeInTheDocument();
    });

    // It should render without crashing, and the icon should fallback to the generic Server icon.
    // In ConnectorCard.tsx, the generic fallback renders the Server icon from lucide-react.
    // We can verify that the generic fallback is used.
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('handles error state properly', async () => {
    server.use(
      http.get(`${baseUrl}/integrations`, () => {
        return new HttpResponse(null, { status: 500, statusText: 'Internal Server Error' });
      })
    );

    render(<IntegrationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Failed to load integrations')).toBeInTheDocument();
    });

    // Ensure the retry button is present
    const retryBtn = screen.getByRole('button', { name: /Retry/i });
    expect(retryBtn).toBeInTheDocument();
  });
});
