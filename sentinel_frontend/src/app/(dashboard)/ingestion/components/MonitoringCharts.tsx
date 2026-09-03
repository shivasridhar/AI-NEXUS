"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
} from 'recharts';
import { format } from 'date-fns';
import { MonitoringMetrics } from '@/types/stage1';

interface MonitoringChartsProps {
  metrics: MonitoringMetrics | undefined;
  isLoading: boolean;
}

export default function MonitoringCharts({ metrics, isLoading }: MonitoringChartsProps) {
  const chartData = metrics?.chartData || [];

  return (
    <div className="glass-panel flex flex-col p-6 h-80 relative border border-slate-200 rounded-3xl bg-white shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-md flex items-center justify-center bg-indigo-50 border-indigo-100 border">
          <Activity className="w-4 h-4 text-indigo-600" />
        </div>
        <h3 className="font-semibold text-slate-800">Event Ingestion Volume</h3>
      </div>

      <div className="flex-1 w-full -ml-4">
        {isLoading && chartData.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-slate-200 rounded"></div>
                  <div className="h-4 bg-slate-200 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          </div>
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorValidated" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis 
                dataKey="time" 
                stroke="#94a3b8" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false} 
                dy={10} 
                tickFormatter={(val) => format(new Date(val), 'HH:mm:ss')}
              />
              <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} dx={-10} />
              <RechartsTooltip
                labelFormatter={(val) => format(new Date(val), 'HH:mm:ss')}
                contentStyle={{ backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(12px)', borderRadius: '10px', border: "1px solid #e2e8f0", color: '#1e293b', boxShadow: '0 4px 16px rgba(0,0,0,0.05)' }}
                itemStyle={{ color: '#1e293b', fontWeight: 600 }}
              />
              <Area type="monotone" dataKey="events" name="Total Events" stackId="2" stroke="#818cf8" fillOpacity={1} fill="url(#colorEvents)" strokeWidth={2} />
              <Area type="monotone" dataKey="validated" name="Validated" stackId="1" stroke="#34d399" fillOpacity={1} fill="url(#colorValidated)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400">No telemetry data available</div>
        )}
      </div>
    </div>
  );
}
