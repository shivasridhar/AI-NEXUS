import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { ConnectorConfigModal } from './ConnectorConfigModal';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { IntegrationResponse } from '@/types/stage1';

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockConnector: IntegrationResponse = {
  id: 'aws-1',
  provider: 'aws',
  name: 'AWS Security Hub',
  status: 'available',
  events_retrieved: 0,
  last_sync_time: null
};

describe('ConnectorConfigModal', () => {
  it('renders nothing when not open', () => {
    const { container } = render(
      <ConnectorConfigModal isOpen={false} onClose={vi.fn()} connector={mockConnector} />,
      { wrapper: createWrapper() }
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders configuration fields for AWS', () => {
    render(
      <ConnectorConfigModal isOpen={true} onClose={vi.fn()} connector={mockConnector} />,
      { wrapper: createWrapper() }
    );

    // Should display the display name from the config map
    expect(screen.getByText('Configure AWS Security Hub')).toBeInTheDocument();
    
    // AWS Account ID field should be present (label text matches)
    expect(screen.getByText(/AWS Account ID/i)).toBeInTheDocument();
  });

  it('validates required fields before submission', async () => {
    render(
      <ConnectorConfigModal isOpen={true} onClose={vi.fn()} connector={mockConnector} />,
      { wrapper: createWrapper() }
    );

    // Assuming the "AWS Account ID" field is required (schema has required: true)
    // HTML form validation should trigger. Since we can't fully simulate native browser 
    // form submission block in jsdom exactly like browsers do, we test for the `required` attribute.
    
    // Using behavioral assertion for accessibility label
    const accountIdInput = screen.getByLabelText(/AWS Account ID \*/i);
    expect(accountIdInput).toBeRequired();
  });
});
