"use client";

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { Search, ArrowUpDown, Filter, Download } from 'lucide-react';
import { format } from 'date-fns';
import { LiveEvent, TableColumnConfig } from '@/types/stage1';

interface LiveEventTableProps {
  events: LiveEvent[];
  columns: TableColumnConfig[];
  isLoading: boolean;
}

export default function LiveEventTable({ events, columns, isLoading }: LiveEventTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const prefersReducedMotion = useReducedMotion();

  const handleSort = (key: string, sortable: boolean) => {
    if (!sortable) return;
    setSortConfig(current => {
      if (current?.key === key) {
        return current.direction === 'asc' ? { key, direction: 'desc' } : null;
      }
      return { key, direction: 'asc' };
    });
  };

  const filteredAndSorted = useMemo(() => {
    let result = [...events];

    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      result = result.filter(event => 
        event.connector.toLowerCase().includes(lowerQuery) ||
        event.eventType.toLowerCase().includes(lowerQuery) ||
        event.message.toLowerCase().includes(lowerQuery)
      );
    }

    if (sortConfig) {
      result.sort((a, b) => {
        const valA = String(a[sortConfig.key as keyof LiveEvent] || '');
        const valB = String(b[sortConfig.key as keyof LiveEvent] || '');
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [events, searchQuery, sortConfig]);

  const renderCellContent = (event: LiveEvent, col: TableColumnConfig) => {
    const val = event[col.key as keyof LiveEvent] as string;

    switch (col.type) {
      case 'date':
        return (
          <span className="font-mono text-xs text-slate-500 font-medium">
            {val ? format(new Date(val), 'MMM d, HH:mm:ss') : 'N/A'}
          </span>
        );
      case 'badge':
        const isSuccess = val === 'SUCCESS';
        const isError = val === 'FAILED' || val === 'BLOCKED';
        return (
          <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
            isSuccess ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 
            isError ? 'bg-rose-50 text-rose-700 border-rose-100' :
            'bg-slate-100 text-slate-600 border-slate-200'
          }`}>
            {val}
          </span>
        );
      case 'severity':
        const severityStyles: Record<string, string> = {
          'INFO': 'bg-blue-50 text-blue-700 border-blue-100',
          'LOW': 'bg-slate-50 text-slate-700 border-slate-200',
          'MEDIUM': 'bg-amber-50 text-amber-700 border-amber-100',
          'HIGH': 'bg-orange-50 text-orange-700 border-orange-100',
          'CRITICAL': 'bg-rose-50 text-rose-700 border-rose-100',
        };
        return (
          <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${severityStyles[val] || severityStyles['INFO']}`}>
            {val}
          </span>
        );
      default:
        return <span className="text-[13px] font-semibold text-slate-600 font-mono">{val}</span>;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
      <div className="p-4 border-b border-slate-100 bg-slate-50 flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            aria-label="Search live events"
            placeholder="Search events..."
            className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-sm"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary text-xs px-4 h-9 flex items-center gap-2 font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button className="btn btn-secondary text-xs px-4 h-9 flex items-center gap-2 font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[800px]">
          <thead className="bg-slate-50 border-b border-slate-100 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            <tr>
              {columns.map((col) => (
                <th 
                  key={col.key} 
                  className={`p-4 ${col.sortable ? 'cursor-pointer hover:text-slate-700 transition-colors group' : ''}`}
                  onClick={() => handleSort(col.key, col.sortable)}
                >
                  <div className="flex items-center gap-1.5">
                    {col.label}
                    {col.sortable && (
                      <ArrowUpDown className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            <AnimatePresence mode="popLayout">
              {isLoading && events.length === 0 ? (
                <motion.tr key="loading" exit={{ opacity: 0 }}>
                  <td colSpan={columns.length} className="p-8 text-center text-slate-500">
                    <div className="animate-pulse flex flex-col items-center gap-2">
                      <div className="h-4 w-32 bg-slate-200 rounded"></div>
                      <div className="text-sm">Loading live events...</div>
                    </div>
                  </td>
                </motion.tr>
              ) : filteredAndSorted.length === 0 ? (
                <motion.tr key="empty" exit={{ opacity: 0 }}>
                  <td colSpan={columns.length} className="p-12 text-center text-slate-500">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center border border-slate-100">
                        <Search className="w-6 h-6 text-slate-400" />
                      </div>
                      <p className="text-sm font-semibold text-slate-700">No events matched</p>
                    </div>
                  </td>
                </motion.tr>
              ) : (
                filteredAndSorted.map((event, index) => (
                  <motion.tr
                    key={event.id}
                    layout
                    initial={{ opacity: 0, y: prefersReducedMotion ? 0 : -10, backgroundColor: 'rgba(79, 70, 229, 0.1)' }}
                    animate={{ opacity: 1, y: 0, backgroundColor: 'rgba(255, 255, 255, 0)' }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="hover:bg-slate-50 transition-colors"
                  >
                    {columns.map((col) => (
                      <td key={col.key} className="p-4">
                        {renderCellContent(event, col)}
                      </td>
                    ))}
                  </motion.tr>
                ))
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}
