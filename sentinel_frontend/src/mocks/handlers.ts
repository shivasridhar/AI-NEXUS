import { http, HttpResponse } from 'msw';
import { IntegrationResponse, IngestionEvent, IngestionMetrics } from '@/types/stage1';

const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://ai-nexus-backend-cndm.onrender.com/api/v1';

export const handlers = [
  // Mock integrations list
  http.get(`${baseUrl}/integrations`, () => {
    return HttpResponse.json([
      {
        id: '1',
        provider: 'aws',
        name: 'AWS Security Hub',
        status: 'active',
        events_retrieved: 1500,
        last_sync_time: new Date().toISOString()
      },
      {
        id: '2',
        provider: 'crowdstrike',
        name: 'CrowdStrike Falcon',
        status: 'available',
        events_retrieved: 0,
        last_sync_time: null
      }
    ]);
  }),

  // Mock configure integration
  http.post(`${baseUrl}/integrations/:provider/configure`, () => {
    return HttpResponse.json({ success: true, message: "Configuration saved successfully" });
  }),

  // Mock ingestion events
  http.get(`${baseUrl}/ingestion/events`, () => {
    return HttpResponse.json([
      {
        id: 'ev-1',
        timestamp: new Date().toISOString(),
        source: 'aws',
        event_type: 'SecurityHub_Finding',
        severity: 'High',
        status: 'Processed'
      },
      {
        id: 'ev-2',
        timestamp: new Date().toISOString(),
        source: 'crowdstrike',
        event_type: 'Detection',
        severity: 'Critical',
        status: 'Dropped'
      }
    ]);
  }),

  // Mock ingestion metrics
  http.get(`${baseUrl}/ingestion/metrics`, () => {
    return HttpResponse.json({
      events_per_second: 42,
      total_events_today: 15000,
      active_sources: 3,
      dropped_events: 150
    });
  }),
];
