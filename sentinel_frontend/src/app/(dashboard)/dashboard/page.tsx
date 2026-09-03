"use client";

import { useDashboardSummary, useRecentFindings, useRecentEvents, useTopAttackPaths, useIdentities, useAnalytics, useMitreTechniques, useComplianceScores } from "@/lib/queries";
import { ShieldCheck, ShieldAlert, GitBranch, Cloud, Users, Activity, BrainCircuit, ArrowRight, FileText, CheckCircle2, ChevronRight, BarChart3, Eye } from "lucide-react";
import Link from "next/link";
import CloudTrailDropzone from "@/components/dashboard/CloudTrailDropzone";
import { useGlobalStore } from "@/lib/store";

export default function CommandCenter() {
  const { data: summary } = useDashboardSummary();
  const { data: findings } = useRecentFindings();
  const { data: events } = useRecentEvents();
  const { data: attackPaths } = useTopAttackPaths();
  const { data: identities } = useIdentities();
  const dashboardView = useGlobalStore((state) => state.dashboardView);
  const setDashboardView = useGlobalStore((state) => state.setDashboardView);
  const { data: mitreData } = useMitreTechniques();
  const { data: complianceData } = useComplianceScores();

  // 1. Posture Calculation
  const totalIdentities = summary?.identities_count || identities?.length || 0;
  const criticalFindings = summary?.critical_risk_count || findings?.filter(f => f.severity === "Critical").length || 0;
  const highFindings = findings?.filter(f => f.severity === "High").length || 0;
  const attackPathsCount = summary?.attack_path_count || attackPaths?.length || 0;

  // Posture Score formula: 100 - (critical * 10) - (high * 5) capped between 10 and 100
  const postureScore = Math.max(10, Math.min(100, 100 - (criticalFindings * 10) - (highFindings * 5)));
  
  const getPostureRating = (score: number) => {
    if (score >= 90) return { label: "Excellent", color: "text-emerald-600 bg-emerald-50 border-emerald-100" };
    if (score >= 70) return { label: "Good", color: "text-amber-600 bg-amber-50 border-amber-100" };
    return { label: "Critical", color: "text-rose-600 bg-rose-50 border-rose-100" };
  };

  const rating = getPostureRating(postureScore);

  return (
    <div className="flex flex-col gap-8 pb-12">
      
      {/* Executive Header with View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {dashboardView === 'executive' ? 'Executive Risk Overview' : 'SOC Analyst Workspace'}
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {dashboardView === 'executive'
              ? 'Enterprise-wide risk posture, KPIs, compliance trends, and strategic recommendations.'
              : 'Incident timeline, MITRE techniques, attack paths, and active threat investigation.'}
          </p>
        </div>
        <div className="flex items-center bg-slate-100 rounded-xl p-1 shrink-0">
          <button
            onClick={() => setDashboardView('executive')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              dashboardView === 'executive'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Executive
          </button>
          <button
            onClick={() => setDashboardView('soc')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              dashboardView === 'soc'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            SOC Analyst
          </button>
        </div>
      </div>

      {dashboardView === 'executive' ? (
      <>
      {/* ═══════════ EXECUTIVE VIEW ═══════════ */}

      {/* 1. TOP SECTION: Posture overview */}
      <section className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-5">
        {/* Posture Score */}
        <Link href="/risk-findings" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Posture Score</span>
            <ShieldCheck className="w-4 h-4 text-indigo-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-[family-name:var(--font-jakarta)] font-bold text-gradient-primary">{postureScore}</span>
            <span className="text-xs font-semibold text-slate-400">/ 100</span>
          </div>
          <span className={`inline-flex w-fit items-center px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${rating.color}`}>
            {rating.label}
          </span>
        </Link>

        {/* Critical Identities */}
        <Link href="/identities" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Identities</span>
            <Users className="w-4 h-4 text-rose-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="text-4xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900">
            {identities?.filter(id => id.risk_score >= 80).length || 0}
          </div>
          <span className="text-[10px] text-slate-400 font-semibold">Identities scored &gt; 80</span>
        </Link>

        {/* High Risk Findings */}
        <Link href="/risk-findings" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Findings</span>
            <ShieldAlert className="w-4 h-4 text-rose-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="text-4xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900">
            {criticalFindings}
          </div>
          <span className="text-[10px] text-slate-400 font-semibold">Active security exposures</span>
        </Link>

        {/* Attack Paths */}
        <Link href="/attack-graph" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Attack Paths</span>
            <GitBranch className="w-4 h-4 text-amber-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="text-4xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900">
            {attackPathsCount}
          </div>
          <span className="text-[10px] text-slate-400 font-semibold">Chained paths mapped</span>
        </Link>

        {/* Cloud Accounts */}
        <Link href="/integrations" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cloud Accounts</span>
            <Cloud className="w-4 h-4 text-indigo-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="text-4xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900">
            {summary?.cloud_accounts_count || 0}
          </div>
          <span className="text-[10px] text-slate-400 font-semibold">Active accounts mapped</span>
        </Link>

        {/* Recent Activity */}
        <Link href="/ingestion" className="bg-white border border-slate-200 rounded-xl p-5 shadow-[var(--shadow-sm)] flex flex-col justify-between h-36 content-card-glow hover:-translate-y-[3px] group/stat cursor-pointer relative">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recent Activity</span>
            <Activity className="w-4 h-4 text-indigo-600 transition-transform duration-200 group-hover/stat:scale-110" />
          </div>
          <div className="text-xl font-[family-name:var(--font-jakarta)] font-bold text-slate-900 truncate">
            {events?.length || 0} events
          </div>
          <span className="text-[10px] text-slate-400 font-semibold">Processed logs stream</span>
        </Link>
      </section>

      {/* 2. SECOND SECTION: Today's Changes */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recently Active Identities */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-[var(--shadow-sm)] flex flex-col content-card-glow hover:-translate-y-[2px]">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span>Recently Active Identities</span>
            <Link href="/identities" className="text-xs text-indigo-600 hover:text-indigo-800 relative group/link overflow-hidden px-1">
              View All
              <span className="absolute bottom-0 left-0 h-px w-full bg-indigo-800 -translate-x-[101%] group-hover/link:translate-x-0 transition-transform duration-200 ease-out"></span>
            </Link>
          </h2>
          <div className="flex flex-col gap-3 flex-1">
            {identities?.slice(0, 4).map(id => (
              <Link href={`/canvas/${id.id}`} key={id.id} className="group/row flex justify-between items-center p-2 rounded-lg bg-slate-50 border border-slate-100 hover-transition hover:bg-[var(--hover-bg-tint)] hover:border-[var(--hover-border)] cursor-pointer">
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-semibold text-slate-900 group-hover/row:text-slate-900 truncate">{(id.arn.split("/").pop() || id.arn).split(":").pop()}</span>
                  <span className="text-[10px] text-slate-400 truncate group-hover/row:text-slate-500">{id.arn.slice(0, 30)}...</span>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded transition-all duration-200 group-hover/row:scale-105 group-hover/row:shadow-[0_0_8px_rgba(var(--hover-shadow-color),0.4)] ${
                  id.risk_score >= 80 
                    ? "bg-rose-50 text-rose-700 group-hover/row:shadow-rose-500/40" 
                    : id.risk_score >= 50 
                    ? "bg-amber-50 text-amber-700 group-hover/row:shadow-amber-500/40" 
                    : "bg-emerald-50 text-emerald-700 group-hover/row:shadow-emerald-500/40"
                }`}>
                  {id.risk_score}
                </span>
              </Link>
            ))}
            {(!identities || identities.length === 0) && (
              <span className="text-xs text-slate-400 my-auto text-center">No active identities</span>
            )}
          </div>
        </div>

        {/* Newest Critical Findings */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-[var(--shadow-sm)] flex flex-col content-card-glow hover:-translate-y-[2px] lg:col-span-2">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span>Newest Critical Findings</span>
            <Link href="/risk-findings" className="text-xs text-indigo-600 hover:text-indigo-800 relative group/link overflow-hidden px-1">
              View All
              <span className="absolute bottom-0 left-0 h-px w-full bg-indigo-800 -translate-x-[101%] group-hover/link:translate-x-0 transition-transform duration-200 ease-out"></span>
            </Link>
          </h2>
          <div className="flex flex-col gap-3 flex-1">
            {findings?.filter(f => f.severity === "Critical" || f.severity === "High").slice(0, 3).map(f => (
              <Link href={`/risk-findings/${f.id}`} key={f.id} className="group/row flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-100 hover-transition hover:bg-[var(--hover-bg-tint)] hover:border-[var(--hover-border)] cursor-pointer">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-900 group-hover/row:text-slate-900 truncate max-w-[200px]">{f.finding_type}</span>
                  <span className="bg-rose-50 text-rose-700 text-[9px] font-bold px-1.5 py-0.5 rounded border border-rose-100 uppercase transition-transform duration-200 group-hover/row:scale-105">
                    {f.severity}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 group-hover/row:text-slate-600 leading-normal">{f.description}</span>
              </Link>
            ))}
            {(!findings || findings.length === 0) && (
              <span className="text-xs text-slate-400 my-auto text-center">No critical findings</span>
            )}
          </div>
        </div>

        {/* SentinelAI Copilot Summary */}
        <div className="bg-indigo-900/5 border border-indigo-900/10 rounded-xl p-6 shadow-sm flex flex-col justify-between copilot-glow hover-transition hover:-translate-y-[2px]">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">SentinelAI Copilot Summary</h2>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed mt-2">
              Our risk engine analyzed {totalIdentities} cloud identities from the last event log stream. We detected {criticalFindings} critical vulnerabilities and {attackPathsCount} potential privilege escalation paths. 
            </p>
            <div className="p-3 bg-white border border-indigo-100 rounded-lg text-[11px] text-indigo-800 leading-normal font-semibold transition-colors duration-200">
              {findings && findings.length > 0 
                ? `✦ Recommendation: Investigate ${findings[0].finding_type.toLowerCase()} related to ${findings[0].identity_arn.split('/').pop()} first.`
                : "✦ Recommendation: Your cloud environment is secure. Continue monitoring for new risks."}
            </div>
          </div>

          <Link
            href="/ai-investigation"
            className="group/btn w-full mt-4 h-9 btn-gradient font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 text-xs"
          >
            Start AI Investigation
            <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover/btn:translate-x-1" />
          </Link>
        </div>
      </section>

      {/* 3. THIRD SECTION: Recommended Actions */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recommended Actions / Risks */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm lg:col-span-2 flex flex-col hover-transition hover:-translate-y-[2px] hover:shadow-[var(--hover-shadow)] hover:border-[var(--hover-border)]">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Top Identity Access Path Risks</h2>
          <div className="flex flex-col gap-3 flex-1 justify-center">
            {attackPaths?.slice(0, 2).map((path, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-slate-900">Chained Privilege Path Detected</span>
                  <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                    {path.nodes?.[0]?.name || "identity-svc"} &rarr; {path.nodes?.[path.nodes.length - 1]?.name || "admin-policy"}
                  </span>
                </div>
                <Link
                  href={`/attack-graph`}
                  className="group/btn text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-600 hover:text-white border border-indigo-100 hover:border-indigo-600 px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1"
                >
                  Inspect Path
                  <ChevronRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover/btn:translate-x-0.5" />
                </Link>
              </div>
            ))}
            {(!attackPaths || attackPaths.length === 0) && (
              <div className="text-center py-6">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                <span className="text-xs text-slate-500 font-semibold">Zero critical attack paths mapped. You are protected.</span>
              </div>
            )}
          </div>
        </div>

        {/* Quick Report & Actions */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between hover-transition hover:-translate-y-[2px] hover:shadow-[var(--hover-shadow)] hover:border-[var(--hover-border)]">
          <div className="flex flex-col gap-3">
            <h2 className="text-sm font-bold text-slate-900">Workspace Operations</h2>
            <p className="text-xs text-slate-500">
              Run manual audit logs reporting or export compliance postures.
            </p>
          </div>
          <div className="flex flex-col gap-2 mt-4">
            <Link
              href="/reports"
              className="group/action relative overflow-hidden h-10 border border-slate-200 text-slate-700 font-semibold rounded-lg flex items-center justify-center gap-2 text-xs hover-transition hover:bg-[var(--hover-bg-tint)] hover:border-[var(--hover-border)] hover:-translate-y-[1px] hover:shadow-sm"
            >
              <FileText className="w-4 h-4 text-slate-400 group-hover/action:text-indigo-600 transition-colors duration-200" />
              Generate Compliance Report
              <ChevronRight className="w-4 h-4 absolute right-4 opacity-0 -translate-x-4 group-hover/action:opacity-100 group-hover/action:translate-x-0 transition-all duration-200 text-indigo-600" />
            </Link>
            <Link
              href="/identities"
              className="group/action relative overflow-hidden h-10 border border-slate-200 text-slate-700 font-semibold rounded-lg flex items-center justify-center gap-2 text-xs hover-transition hover:bg-[var(--hover-bg-tint)] hover:border-[var(--hover-border)] hover:-translate-y-[1px] hover:shadow-sm"
            >
              <Users className="w-4 h-4 text-slate-400 group-hover/action:text-indigo-600 transition-colors duration-200" />
              Search All Identities
              <ChevronRight className="w-4 h-4 absolute right-4 opacity-0 -translate-x-4 group-hover/action:opacity-100 group-hover/action:translate-x-0 transition-all duration-200 text-indigo-600" />
            </Link>
          </div>
        </div>
      </section>

      {/* 4. FOURTH SECTION: Threat Timeline */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-[var(--shadow-sm)] content-card-glow hover:-translate-y-[2px] relative flex flex-col">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Activity className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-800">Threat Ingestion Activity Stream</h2>
          </div>
          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded">
            Live Stream Connected
          </span>
        </div>
        <div className="p-6">
          <CloudTrailDropzone />
        </div>
      </section>

      </>
      ) : (
      <>
      {/* ═══════════ SOC ANALYST VIEW ═══════════ */}

      {/* SOC 1. Incident Timeline */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Threats Panel */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm lg:col-span-2 flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            Active Threat Timeline
          </h2>
          <div className="flex flex-col gap-2 flex-1">
            {events?.slice(0, 8).map((event: any, idx: number) => (
              <div key={event.id || idx} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100 hover:bg-slate-100 transition-colors">
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                  event.severity === 'CRITICAL' ? 'bg-rose-500' :
                  event.severity === 'HIGH' ? 'bg-amber-500' :
                  event.severity === 'MEDIUM' ? 'bg-yellow-400' : 'bg-emerald-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-semibold text-slate-900 truncate block">{event.event_name || event.eventType || 'Event'}</span>
                  <span className="text-[10px] text-slate-400">{event.identity_arn || event.actor || 'Unknown actor'}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 shrink-0">
                  {event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}) : ''}
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                  event.severity === 'CRITICAL' ? 'bg-rose-50 text-rose-700' :
                  event.severity === 'HIGH' ? 'bg-amber-50 text-amber-700' :
                  'bg-slate-100 text-slate-500'
                }`}>{event.severity || 'INFO'}</span>
              </div>
            ))}
            {(!events || events.length === 0) && (
              <div className="text-center py-8 text-xs text-slate-400">No recent events. Upload CloudTrail data to begin monitoring.</div>
            )}
          </div>
        </div>

        {/* MITRE ATT&CK Tactics — Live Data */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-indigo-600" />
            MITRE ATT&CK Techniques
            {mitreData?.total ? (
              <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded ml-auto">{mitreData.total} detected</span>
            ) : null}
          </h2>
          <div className="flex flex-col gap-2 flex-1">
            {mitreData?.techniques && mitreData.techniques.length > 0 ? (
              mitreData.techniques.slice(0, 8).map((t: any, idx: number) => (
                <div key={t.technique_id || idx} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-slate-800">{t.technique_name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{t.technique_id} &middot; {t.tactic}</span>
                  </div>
                  <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">{t.tactic_id}</span>
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">
                No MITRE techniques detected yet. Upload security events to generate mappings.
              </div>
            )}
          </div>

          {/* Compliance Summary */}
          {complianceData?.compliance_scores && Object.keys(complianceData.compliance_scores).length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-slate-700 mb-3">Compliance Posture</h3>
              <div className="flex flex-col gap-2">
                {Object.entries(complianceData.compliance_scores).map(([framework, data]: [string, any]) => (
                  <div key={framework} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-xs font-semibold text-slate-700">{framework}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-400">{data.violated_controls} violations</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        data.score >= 80 ? 'bg-emerald-50 text-emerald-700' :
                        data.score >= 50 ? 'bg-amber-50 text-amber-700' :
                        'bg-rose-50 text-rose-700'
                      }`}>{data.score}/100</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* SOC 2. Identity Risk + Attack Paths */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* High Risk Identities for Investigation */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Users className="w-4 h-4 text-rose-600" />
              Identities Requiring Investigation
            </span>
            <Link href="/identities" className="text-xs text-indigo-600 hover:text-indigo-800">View All</Link>
          </h2>
          <div className="flex flex-col gap-2 flex-1">
            {identities?.filter((id: any) => id.risk_score >= 40).slice(0, 6).map((id: any) => (
              <Link href={`/canvas/${id.id}`} key={id.id} className="group flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100 hover:bg-indigo-50/50 hover:border-indigo-200 transition-all">
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-xs font-bold text-slate-900 truncate">{(id.arn.split("/").pop() || id.arn).split(":").pop()}</span>
                  <span className="text-[10px] text-slate-400 font-mono truncate">{id.arn}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">{id.identity_type}</span>
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                    id.risk_score >= 80 ? 'bg-rose-50 text-rose-700' :
                    id.risk_score >= 60 ? 'bg-amber-50 text-amber-700' :
                    'bg-yellow-50 text-yellow-700'
                  }`}>{id.risk_score}</span>
                </div>
              </Link>
            ))}
            {(!identities || identities.filter((id: any) => id.risk_score >= 40).length === 0) && (
              <div className="text-center py-6 text-xs text-slate-400">No high-risk identities detected.</div>
            )}
          </div>
        </div>

        {/* Attack Paths Mapped */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-amber-600" />
              Attack Paths &amp; Lateral Movement
            </span>
            <Link href="/attack-graph" className="text-xs text-indigo-600 hover:text-indigo-800">Inspect Graph</Link>
          </h2>
          <div className="flex flex-col gap-2 flex-1">
            {attackPaths?.slice(0, 5).map((path: any, idx: number) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-900">Privilege Escalation Path #{idx + 1}</span>
                  <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
                    {path.nodes?.length || 0} hops
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {path.nodes?.[0]?.name || 'source'} &rarr; {path.nodes?.[path.nodes.length - 1]?.name || 'target'}
                </span>
              </div>
            ))}
            {(!attackPaths || attackPaths.length === 0) && (
              <div className="flex flex-col items-center justify-center py-8 gap-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                <span className="text-xs text-slate-500 font-semibold">No attack paths detected.</span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* SOC 3. Quick Actions */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/ai-investigation" className="bg-indigo-900/5 border border-indigo-200 rounded-xl p-6 flex flex-col gap-3 hover:bg-indigo-50 transition-all group">
          <BrainCircuit className="w-6 h-6 text-indigo-600" />
          <h3 className="text-sm font-bold text-slate-900">Start AI Investigation</h3>
          <p className="text-xs text-slate-500">Query the Copilot about specific identities, lateral movement, or threat analysis.</p>
          <span className="text-xs font-bold text-indigo-600 flex items-center gap-1 group-hover:gap-2 transition-all">
            Open Copilot <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>
        <Link href="/ingestion" className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-3 hover:border-indigo-200 transition-all group">
          <Activity className="w-6 h-6 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900">Ingestion Monitor</h3>
          <p className="text-xs text-slate-500">View live event pipeline, connector health, and validation metrics.</p>
          <span className="text-xs font-bold text-indigo-600 flex items-center gap-1 group-hover:gap-2 transition-all">
            View Pipeline <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>
        <Link href="/cloudtrail" className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-3 hover:border-indigo-200 transition-all group">
          <Cloud className="w-6 h-6 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Upload CloudTrail</h3>
          <p className="text-xs text-slate-500">Drag and drop CloudTrail JSON logs for immediate analysis.</p>
          <span className="text-xs font-bold text-indigo-600 flex items-center gap-1 group-hover:gap-2 transition-all">
            Upload Data <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>
      </section>

      </>
      )}

    </div>
  );
}
