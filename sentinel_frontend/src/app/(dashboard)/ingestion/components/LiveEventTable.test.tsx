import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LiveEventTable from './LiveEventTable';
import React from 'react';
import { LiveEvent, TableColumnConfig } from '@/types/stage1';

const mockColumns: TableColumnConfig[] = [
  { key: 'timestamp', label: 'Time', type: 'date', sortable: true },
  { key: 'connector', label: 'Source', type: 'string', sortable: true },
  { key: 'message', label: 'Message', type: 'string', sortable: false },
];

const mockEvents: LiveEvent[] = [
  {
    id: 'evt-1',
    timestamp: new Date().toISOString(),
    connector: 'AWS CloudTrail',
    eventType: 'Login',
    severity: 'INFO',
    status: 'SUCCESS',
    message: 'User login'
  },
  {
    id: 'evt-2',
    timestamp: new Date().toISOString(),
    connector: 'Okta',
    eventType: 'Failed Login',
    severity: 'HIGH',
    status: 'BLOCKED',
    message: 'Failed login attempt'
  }
];

describe('LiveEventTable', () => {
  it('renders loading state when isLoading is true and events are empty', () => {
    render(<LiveEventTable events={[]} columns={mockColumns} isLoading={true} />);
    expect(screen.getByText('Loading live events...')).toBeInTheDocument();
  });

  it('renders events correctly', () => {
    render(<LiveEventTable events={mockEvents} columns={mockColumns} isLoading={false} />);
    expect(screen.getByText('AWS CloudTrail')).toBeInTheDocument();
    expect(screen.getByText('User login')).toBeInTheDocument();
    expect(screen.getByText('Okta')).toBeInTheDocument();
  });

  it('filters events based on search query without remounting', () => {
    const { rerender } = render(<LiveEventTable events={mockEvents} columns={mockColumns} isLoading={false} />);
    
    // Using behavioral assertion for accessibility label
    const searchInput = screen.getByLabelText('Search live events');
    fireEvent.change(searchInput, { target: { value: 'aws' } });

    // Okta should be filtered out
    expect(screen.getByText('AWS CloudTrail')).toBeInTheDocument();
    expect(screen.queryByText('Okta')).not.toBeInTheDocument();

    // Rerender with new data (simulating a refetch), state should be preserved
    const newEvents = [
      ...mockEvents,
      {
        id: 'evt-3',
        timestamp: new Date().toISOString(),
        connector: 'AWS Config',
        eventType: 'Change',
        severity: 'LOW',
        status: 'SUCCESS',
        message: 'Config updated'
      }
    ];

    rerender(<LiveEventTable events={newEvents} columns={mockColumns} isLoading={false} />);

    // The search term should still be applied, meaning Okta is still hidden, and both AWS items are shown
    expect(screen.queryByText('Okta')).not.toBeInTheDocument();
    expect(screen.getByText('AWS CloudTrail')).toBeInTheDocument();
    expect(screen.getByText('AWS Config')).toBeInTheDocument();
    
    // Check if input value is still 'aws'
    expect((searchInput as HTMLInputElement).value).toBe('aws');
  });

  it('sorts events correctly', () => {
    render(<LiveEventTable events={mockEvents} columns={mockColumns} isLoading={false} />);
    
    // Click on the Source column to sort
    const sourceHeader = screen.getByText('Source');
    fireEvent.click(sourceHeader); // Ascending (AWS -> Okta)
    
    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1] is AWS, rows[2] is Okta
    expect(rows[1]).toHaveTextContent('AWS CloudTrail');
    expect(rows[2]).toHaveTextContent('Okta');
    
    fireEvent.click(sourceHeader); // Descending (Okta -> AWS)
    
    const rowsDesc = screen.getAllByRole('row');
    expect(rowsDesc[1]).toHaveTextContent('Okta');
    expect(rowsDesc[2]).toHaveTextContent('AWS CloudTrail');
  });
});
