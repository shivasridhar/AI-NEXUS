"use client";

import React, { useState } from 'react';
import { Activity, ServerCrash, RefreshCw } from 'lucide-react';
import { useGlobalStore } from '@/lib/store';
import { useMonitoringConfig, useMonitoringMetrics, useLiveEvents } from '@/lib/queries/stage1';

import PipelineVisualizer from './components/PipelineVisualizer';
import MonitoringCharts from './components/MonitoringCharts';
import LiveEventTable from './components/LiveEventTable';

export default function IngestionMonitorPage() {
  const { autoRefreshInterval, setAutoRefreshInterval } = useGlobalStore();
  const [isManualRefreshing, setIsManualRefreshing] = useState(false);

  // Queries
  const { 
    data: configData, 
    isLoading: isConfigLoading,
    isError: isConfigError,
    refetch: refetchConfig
  } = useMonitoringConfig();

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    isError: isMetricsError,
    refetch: refetchMetrics
  } = useMonitoringMetrics(autoRefreshInterval);

  const {
    data: eventsData,
    isLoading: isEventsLoading,
    isError: isEventsError,
    refetch: refetchEvents
  } = useLiveEvents(autoRefreshInterval, 50);

  const handleManualRefresh = async () => {
    setIsManualRefreshing(true);
    await Promise.all([
      refetchConfig(),
      refetchMetrics(),
      refetchEvents()
    ]);
    setTimeout(() => setIsManualRefreshing(false), 500); // Visual feedback delay
  };

  const isBackendOffline = isConfigError || isMetricsError || isEventsError;

  return (
    <div className="flex flex-col gap-8 pb-12 min-h-screen">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-indigo-600" />
            Ingestion Monitor
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Live telemetry and health for data ingestion pipelines.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-2 h-9 shadow-sm">
            <span className="text-[10px] font-bold uppercase text-slate-400">Auto Refresh</span>
            <select 
              className="text-xs font-semibold text-slate-700 bg-transparent outline-none cursor-pointer"
              value={autoRefreshInterval || 0}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                setAutoRefreshInterval(val === 0 ? null : val);
              }}
            >
              <option value={0}>Off</option>
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
              <option value={30000}>30s</option>
            </select>
          </div>
          <button 
            onClick={handleManualRefresh}
            disabled={isManualRefreshing}
            className="btn btn-primary text-xs px-4 h-9 flex items-center gap-2 font-semibold disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isManualRefreshing ? 'animate-spin' : ''}`} />
            Refresh Now
          </button>
        </div>
      </div>

      {isBackendOffline && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center gap-3">
          <ServerCrash className="w-5 h-5 text-rose-600" />
          <div>
            <h4 className="text-sm font-bold text-rose-900">Backend Connection Error</h4>
            <p className="text-xs text-rose-700">Unable to retrieve live monitoring telemetry. Check API connectivity.</p>
          </div>
        </div>
      )}

      {/* Top KPI Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard 
          title="Total Events Processed" 
          value={metricsData?.totalEvents} 
          desc="All-time volume" 
          isLoading={isMetricsLoading} 
        />
        <StatCard 
          title="Events / Minute" 
          value={metricsData?.eventsPerMinute} 
          desc="Current throughput" 
          isLoading={isMetricsLoading} 
        />
        <StatCard 
          title="Validation Success Rate" 
          value={metricsData ? `${metricsData.validationSuccessRate.toFixed(1)}%` : undefined} 
          desc="Schema conformance" 
          isLoading={isMetricsLoading} 
        />
        <StatCard 
          title="Active Connectors" 
          value={metricsData?.activeConnectors} 
          desc="Currently syncing" 
          isLoading={isMetricsLoading} 
        />
      </div>

      {/* Pipeline & Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-panel p-6 border border-slate-200 rounded-3xl bg-white shadow-sm flex flex-col">
          <h3 className="font-semibold text-slate-800 mb-2">Pipeline Topology</h3>
          <p className="text-xs text-slate-500 mb-4">Real-time stage health and processing flow.</p>
          <div className="flex-1 flex items-center">
            <PipelineVisualizer stages={configData?.stages || []} isLoading={isConfigLoading} />
          </div>
        </div>
        <div className="lg:col-span-1">
          <MonitoringCharts metrics={metricsData} isLoading={isMetricsLoading} />
        </div>
      </div>

      {/* Live Event Feed */}
      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Live Event Feed</h3>
          <p className="text-xs text-slate-500">Real-time normalized events exiting the pipeline.</p>
        </div>
        <LiveEventTable 
          events={eventsData || []} 
          columns={configData?.columns || []} 
          isLoading={isEventsLoading || isConfigLoading} 
        />
      </div>
    </div>
  );
}

function StatCard({ title, value, desc, isLoading }: { title: string; value?: string | number; desc: string; isLoading: boolean }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-2 hover:border-slate-300 transition-all group">
      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{title}</span>
      <div className="flex items-baseline gap-2">
        {isLoading || value === undefined ? (
          <div className="h-8 w-24 bg-slate-100 rounded animate-pulse"></div>
        ) : (
          <div className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </div>
        )}
      </div>
      <span className="text-xs text-slate-500">{desc}</span>
    </div>
  );
}
