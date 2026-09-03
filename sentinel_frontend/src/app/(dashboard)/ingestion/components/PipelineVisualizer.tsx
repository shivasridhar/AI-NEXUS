"use client";

import React from 'react';
import { PipelineStage } from '@/types/stage1';
import { ArrowRight, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';

interface PipelineVisualizerProps {
  stages: PipelineStage[];
  isLoading: boolean;
}

export default function PipelineVisualizer({ stages, isLoading }: PipelineVisualizerProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-4 py-6 w-full overflow-x-auto">
        {Array.from({ length: 4 }).map((_, i) => (
          <React.Fragment key={i}>
            <div className="h-16 w-32 bg-slate-100 rounded-xl animate-pulse shrink-0 border border-slate-200"></div>
            {i < 3 && <div className="h-0.5 w-8 bg-slate-100 animate-pulse shrink-0"></div>}
          </React.Fragment>
        ))}
      </div>
    );
  }

  if (stages.length === 0) return null;

  return (
    <div className="flex items-center gap-3 py-4 w-full overflow-x-auto scrollbar-none">
      {stages.map((stage, index) => {
        const isHealthy = stage.status === 'healthy';
        const isDegraded = stage.status === 'degraded';
        
        return (
          <React.Fragment key={stage.id}>
            <div className={`relative flex flex-col min-w-[140px] p-3 rounded-xl border shrink-0 transition-colors ${
              isHealthy ? 'bg-emerald-50/50 border-emerald-100' :
              isDegraded ? 'bg-amber-50/50 border-amber-200' :
              'bg-rose-50/50 border-rose-200'
            }`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">{stage.name}</span>
                {isHealthy ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : isDegraded ? (
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-500" />
                )}
              </div>
              <p className="text-[10px] text-slate-500 leading-tight">
                {stage.description}
              </p>
              
              {/* Status Indicator Bar */}
              <div className="absolute bottom-0 left-0 right-0 h-1 rounded-b-xl overflow-hidden opacity-50">
                <div className={`h-full w-full ${
                  isHealthy ? 'bg-emerald-400' :
                  isDegraded ? 'bg-amber-400' :
                  'bg-rose-400'
                }`}></div>
              </div>
            </div>

            {index < stages.length - 1 && (
              <div className="flex items-center justify-center shrink-0 text-slate-300">
                <ArrowRight className="w-5 h-5" />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
