"use client";

import { use, useState, useEffect } from "react";
import { ArrowLeft, ShieldAlert, Clock, Info, ExternalLink, Download } from "lucide-react";
import { useFindingDetails, useExportReport } from "@/lib/queries";
import Link from "next/link";
import { EvidencePanel, ConfidencePanel, RiskFactorsPanel, GraphMetricsPanel } from "@/components/findings/FindingPanels";

export default function FindingDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { data: finding, isLoading, error } = useFindingDetails(resolvedParams.id);
  const [isGraphEngineEnabled, setIsGraphEngineEnabled] = useState(false);
  const exportReport = useExportReport();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!finding) return;
    setIsDownloading(true);
    try {
      await exportReport.mutateAsync({
        finding_id: finding.id,
        filename: `finding_report_${finding.id.slice(0, 8)}.pdf`
      });
    } catch (err) {
      console.error("Failed to download PDF report:", err);
    } finally {
      setIsDownloading(false);
    }
  };

  useEffect(() => {
    // Check if Graph Evidence Engine is enabled via environment variable
    if (process.env.NEXT_PUBLIC_ENABLE_GRAPH_EVIDENCE_ENGINE === 'true') {
      setIsGraphEngineEnabled(true);
    }
  }, []);

  if (isLoading) {
    return <div className="p-12 text-center text-slate-500">Loading finding details...</div>;
  }

  if (error || !finding) {
    return <div className="p-12 text-center text-rose-500 font-bold">Failed to load finding details or finding not found.</div>;
  }

  const getSeverityStyle = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL": return "text-rose-700 bg-rose-50 border-rose-100";
      case "HIGH": return "text-amber-700 bg-amber-50 border-amber-100";
      case "MEDIUM": return "text-yellow-700 bg-yellow-50 border-yellow-100";
      default: return "text-emerald-700 bg-emerald-50 border-emerald-100";
    }
  };

  return (
    <div className="animate-in fade-in duration-500 pb-12 flex flex-col gap-6 max-w-5xl mx-auto">
      
      {/* Navigation */}
      <div>
        <Link href="/risk-findings" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Risk Center
        </Link>
      </div>

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getSeverityStyle(finding.severity)}`}>
              {finding.severity}
            </span>
            <span className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider">{finding.id.split('-')[0]}</span>
          </div>
          
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{finding.finding_type}</h1>
            <p className="text-slate-600 mt-2 max-w-2xl leading-relaxed">{finding.description}</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 min-w-[200px]">
          <Link 
            href={`/ai-investigation?identityId=${finding.identity_id}`}
            className="w-full h-10 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center justify-center gap-2 text-sm font-semibold transition-all shadow-sm"
          >
            AI Investigate
            <ExternalLink className="w-4 h-4" />
          </Link>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="w-full h-10 border border-slate-200 hover:border-indigo-400 text-slate-700 hover:text-indigo-600 rounded-lg flex items-center justify-center gap-2 text-sm font-semibold transition-all bg-white shadow-sm disabled:opacity-50"
          >
            {isDownloading ? (
              <>
                <Clock className="w-4 h-4 animate-spin text-indigo-600" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Download Report
              </>
            )}
          </button>
          <div className="text-xs text-slate-500 flex items-center gap-2 mt-2">
            <Clock className="w-4 h-4" />
            Detected: {new Date(finding.created_at).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Basic Finding Data (Always Visible) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Identity Information</h3>
          <div className="font-mono text-sm text-slate-800 break-all bg-slate-50 p-3 rounded-lg border border-slate-100">
            {finding.identity_id}
          </div>
        </div>
        
        {finding.event_reference && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Event Reference</h3>
            <div className="font-mono text-sm text-slate-800 break-all bg-slate-50 p-3 rounded-lg border border-slate-100">
              {finding.event_reference}
            </div>
          </div>
        )}
      </div>

      {/* Additive Graph Evidence Engine Panels (Feature Flagged) */}
      {isGraphEngineEnabled && finding.evidence_status && (
        <div className="mt-8 flex flex-col gap-6">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
            <ShieldAlert className="w-5 h-5 text-indigo-600" />
            <h2 className="text-xl font-bold text-slate-900">Graph Evidence & Explainability</h2>
            <span className="ml-2 px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] font-bold rounded uppercase border border-indigo-100">
              Powered by Graph Engine
            </span>
          </div>

          <EvidencePanel evidence={finding} />
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ConfidencePanel confidence={finding.confidence} />
            <GraphMetricsPanel metrics={finding.graph_metrics} />
          </div>
          
          <RiskFactorsPanel riskFactors={finding.risk_factors} />
        </div>
      )}

    </div>
  );
}
