"use client";

import { useState } from "react";
import { useIdentities, useExportReport } from "@/lib/queries";
import { Search, Download, ChevronDown, ChevronRight, BrainCircuit, GitBranch, Shield, Eye, Settings2 } from "lucide-react";
import Link from "next/link";

const getRiskConfig = (score: number) => {
  if (score >= 80) return { label: "Critical", style: "bg-rose-50 text-rose-700 border-rose-100" };
  if (score >= 60) return { label: "High", style: "bg-amber-50 text-amber-700 border-amber-100" };
  if (score >= 40) return { label: "Medium", style: "bg-yellow-50 text-yellow-700 border-yellow-100" };
  return { label: "Low", style: "bg-emerald-50 text-emerald-700 border-emerald-100" };
};

export default function MachineIdentitiesPage() {
  const { data: identitiesData, isLoading } = useIdentities();
  const exportReport = useExportReport();
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownloadIdentityReport = async (identityId: string) => {
    setDownloadingId(identityId);
    try {
      await exportReport.mutateAsync({
        identity_id: identityId,
        filename: `identity_report_${identityId.slice(0, 8)}.pdf`
      });
    } catch (err) {
      console.error("Failed to download identity PDF report:", err);
    } finally {
      setDownloadingId(null);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [cloudFilter, setCloudFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskSort, setRiskSort] = useState("desc");

  // Format AWS IAM data or fall back to mock list
  const activeIdentities = identitiesData || [];

  const filteredIdentities = activeIdentities
    .filter(id => {
      // 1. Search Query
      const matchesSearch = id.arn.toLowerCase().includes(searchQuery.toLowerCase());
      
      // 2. Severity Filter
      let matchesSeverity = true;
      if (severityFilter === "critical") matchesSeverity = id.risk_score >= 80;
      else if (severityFilter === "high") matchesSeverity = id.risk_score >= 60 && id.risk_score < 80;
      else if (severityFilter === "medium") matchesSeverity = id.risk_score >= 40 && id.risk_score < 60;
      else if (severityFilter === "low") matchesSeverity = id.risk_score < 40;

      // 3. Cloud Filter
      let matchesCloud = true;
      if (cloudFilter === "aws") matchesCloud = id.arn.includes("aws");
      else if (cloudFilter === "gcp") matchesCloud = id.arn.includes("gcp");

      // 4. Status Filter
      let matchesStatus = true;
      if (statusFilter === "alert") matchesStatus = id.risk_score >= 60;
      else if (statusFilter === "healthy") matchesStatus = id.risk_score < 60;

      return matchesSearch && matchesSeverity && matchesCloud && matchesStatus;
    })
    .sort((a, b) => {
      return riskSort === "desc" ? b.risk_score - a.risk_score : a.risk_score - b.risk_score;
    });

  return (
    <div className="animate-in fade-in duration-500 pb-12 flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Identity Center</h1>
          <p className="text-slate-500 mt-1 text-sm">Discovered machine identities, execution profiles, and risk vectors.</p>
        </div>
        
        {/* Stats Row */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="bg-white border border-slate-200 rounded-lg px-4 py-2 flex items-center gap-3 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Discovered</span>
            <span className="text-lg font-bold text-slate-800">{activeIdentities.length}</span>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg px-4 py-2 flex items-center gap-3 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Risk</span>
            <span className="text-lg font-bold text-rose-600">
              {activeIdentities.filter(id => id.risk_score >= 80).length}
            </span>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg px-4 py-2 flex items-center gap-3 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">High Risk</span>
            <span className="text-lg font-bold text-amber-600">
              {activeIdentities.filter(id => id.risk_score >= 60 && id.risk_score < 80).length}
            </span>
          </div>
        </div>
      </div>

      {/* Advanced Filters */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex flex-wrap items-center gap-4 bg-slate-50">
          
          {/* Cloud Select */}
          <div className="flex flex-col gap-1 min-w-[120px]">
            <label className="text-[10px] font-bold text-slate-400 uppercase">Cloud Provider</label>
            <select
              value={cloudFilter}
              onChange={(e) => setCloudFilter(e.target.value)}
              className="input-field h-8 text-xs py-1"
            >
              <option value="all">All Clouds</option>
              <option value="aws">AWS IAM</option>
              <option value="gcp">GCP (Coming Soon)</option>
            </select>
          </div>

          {/* Severity Select */}
          <div className="flex flex-col gap-1 min-w-[120px]">
            <label className="text-[10px] font-bold text-slate-400 uppercase">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="input-field h-8 text-xs py-1"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical (80+)</option>
              <option value="high">High (60-79)</option>
              <option value="medium">Medium (40-59)</option>
              <option value="low">Low (&lt;40)</option>
            </select>
          </div>

          {/* Status Select */}
          <div className="flex flex-col gap-1 min-w-[120px]">
            <label className="text-[10px] font-bold text-slate-400 uppercase">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-field h-8 text-xs py-1"
            >
              <option value="all">All Statuses</option>
              <option value="alert">Requires Attention</option>
              <option value="healthy">Healthy</option>
            </select>
          </div>

          {/* Sort Select */}
          <div className="flex flex-col gap-1 min-w-[120px]">
            <label className="text-[10px] font-bold text-slate-400 uppercase">Risk Sort</label>
            <select
              value={riskSort}
              onChange={(e) => setRiskSort(e.target.value)}
              className="input-field h-8 text-xs py-1"
            >
              <option value="desc">Highest Risk</option>
              <option value="asc">Lowest Risk</option>
            </select>
          </div>

          {/* Search bar */}
          <div className="flex-1 flex flex-col gap-1 min-w-[200px] lg:ml-auto">
            <label className="text-[10px] font-bold text-slate-400 uppercase">Search</label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by ARN, role name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 input-field h-8 text-xs"
              />
            </div>
          </div>
        </div>

        {/* Table View */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="p-4">Identity Profile</th>
                <th className="p-4">Severity / Score</th>
                <th className="p-4">ARN</th>
                <th className="p-4">Provider</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {filteredIdentities.map(id => {
                const config = getRiskConfig(id.risk_score);
                return (
                  <tr key={id.id} className="hover:bg-slate-50 transition-all group">
                    <td className="p-4">
                      <div className="flex flex-col">
                        <span className="font-semibold text-slate-900">{(id.arn.split("/").pop() || id.arn).split(":").pop()}</span>
                        <span className="text-[10px] text-slate-400 font-mono mt-0.5">{id.arn.slice(0, 45)}...</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.style}`}>
                        {config.label} ({id.risk_score})
                      </span>
                    </td>
                    <td className="p-4 text-xs font-mono text-slate-500">{id.arn}</td>
                    <td className="p-4 text-xs font-semibold text-slate-600">AWS IAM</td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                        {/* Explain Button */}
                        <Link
                          href={`/ai-investigation?identityId=${id.id}`}
                          className="h-8 px-3 border border-slate-200 hover:border-indigo-400 text-slate-700 hover:text-indigo-600 rounded-lg flex items-center gap-1.5 text-xs bg-white transition-all shadow-sm"
                        >
                          <BrainCircuit className="w-3.5 h-3.5" />
                          AI Explain
                        </Link>
                        {/* Graph Button */}
                        <Link
                          href={`/canvas/${id.id}`}
                          className="h-8 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-1.5 text-xs transition-all shadow-sm shadow-indigo-100 font-semibold"
                        >
                          <GitBranch className="w-3.5 h-3.5" />
                          Graph
                        </Link>
                        {/* Download PDF Button */}
                        <button
                          onClick={() => handleDownloadIdentityReport(id.id)}
                          disabled={downloadingId !== null}
                          className="h-8 w-8 border border-slate-200 hover:border-indigo-400 text-slate-700 hover:text-indigo-600 rounded-lg flex items-center justify-center bg-white transition-all shadow-sm disabled:opacity-50"
                          title="Download Security Profile PDF"
                        >
                          {downloadingId === id.id ? (
                            <div className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredIdentities.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-400 text-xs">
                    No machine identities match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
