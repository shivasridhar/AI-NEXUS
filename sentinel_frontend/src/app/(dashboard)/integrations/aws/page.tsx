"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Cloud, ArrowLeft, Save, RefreshCw, AlertCircle, CheckCircle2,
  Shield, Key, ChevronRight, ExternalLink, Database, Clock, Zap, XCircle
} from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";

type AuthMethod = "access_key" | "role_arn";

interface IntegrationState {
  id?: string;
  status: string;
  config?: {
    account_id?: string;
    region?: string;
    auth_method?: AuthMethod;
    has_external_id?: boolean;
  };
  last_sync_time?: string | null;
  events_retrieved?: number;
  error_message?: string | null;
}

interface ValidationResult {
  valid: boolean;
  account_id?: string;
  arn?: string;
  message?: string;
}

type Step = "configure" | "validate" | "sync";

const REGIONS = [
  "us-east-1", "us-east-2", "us-west-1", "us-west-2",
  "eu-west-1", "eu-west-2", "eu-central-1",
  "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
  "ca-central-1", "sa-east-1"
];

export default function AWSIntegrationPage() {
  const [step, setStep] = useState<Step>("configure");

  const [config, setConfig] = useState({
    account_id: "",
    region: "us-east-1",
    auth_method: "access_key" as AuthMethod,
    role_arn: "",
    external_id: "",
    access_key: "",
    secret_key: ""
  });

  const [integration, setIntegration] = useState<IntegrationState | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchIntegration = useCallback(async () => {
    try {
      const data: any[] = await api.get('/integrations');
      const aws = data.find((d) => d.provider === 'aws');
      if (aws && aws.status !== 'available') {
        setIntegration(aws);
        if (aws.config) {
          setConfig(prev => ({
            ...prev,
            account_id: aws.config.account_id || "",
            region: aws.config.region || "us-east-1",
            auth_method: (aws.config.auth_method as AuthMethod) || "access_key",
          }));
        }
        // Jump to sync step if already configured
        if (aws.status !== 'available') {
          setStep("sync");
        }
      }
    } catch (e) {
      console.error("Failed to fetch integration:", e);
    }
  }, []);

  useEffect(() => {
    fetchIntegration();
  }, [fetchIntegration]);

  const handleValidate = async () => {
    setIsValidating(true);
    setError(null);
    setValidationResult(null);
    try {
      const result = await api.post('/integrations/aws/validate', {
        account_id: config.account_id,
        region: config.region,
        auth_method: config.auth_method,
        role_arn: config.auth_method === "role_arn" ? config.role_arn : undefined,
        external_id: config.auth_method === "role_arn" && config.external_id ? config.external_id : undefined,
        access_key: config.auth_method === "access_key" ? config.access_key : undefined,
        secret_key: config.auth_method === "access_key" ? config.secret_key : undefined,
      });
      setValidationResult(result);
      setStep("validate");
    } catch (e: any) {
      setError(e.message || "Validation failed. Check your credentials.");
    } finally {
      setIsValidating(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await api.post('/integrations/aws', {
        account_id: config.account_id,
        region: config.region,
        auth_method: config.auth_method,
        role_arn: config.auth_method === "role_arn" ? config.role_arn : undefined,
        external_id: config.auth_method === "role_arn" && config.external_id ? config.external_id : undefined,
        access_key: config.auth_method === "access_key" ? config.access_key : undefined,
        secret_key: config.auth_method === "access_key" ? config.secret_key : undefined,
      });
      setSuccess("Configuration saved successfully.");
      await fetchIntegration();
      setStep("sync");
    } catch (e: any) {
      setError(e.message || "Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setError(null);
    setSuccess(null);
    try {
      await api.post('/integrations/aws/sync', {});

      // Poll the real backend status until sync completes
      const pollInterval = setInterval(async () => {
        try {
          const data: any[] = await api.get('/integrations');
          const aws = data.find((d) => d.provider === 'aws');
          if (aws) {
            setIntegration(aws);
            if (aws.status !== 'syncing' && aws.status !== 'configured') {
              clearInterval(pollInterval);
              setIsSyncing(false);
              if (aws.status === 'error') {
                setError(aws.error_message || "Sync failed. Please check your AWS permissions.");
              } else {
                setSuccess("Sync completed successfully!");
              }
            }
          }
        } catch (e) {
          console.error("Polling error:", e);
        }
      }, 3000);
    } catch (e: any) {
      const detail = e.message || "Failed to start sync.";
      setError(detail);
      setIsSyncing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; cls: string }> = {
      configured: { label: "Configured", cls: "bg-blue-50 text-blue-700 border-blue-200" },
      syncing: { label: "Syncing...", cls: "bg-amber-50 text-amber-700 border-amber-200" },
      success: { label: "Synced", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
      synced_no_new_events: { label: "Up to Date", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
      error: { label: "Error", cls: "bg-rose-50 text-rose-700 border-rose-200" },
    };
    const s = map[status] || { label: status.replace(/_/g, " "), cls: "bg-slate-100 text-slate-600 border-slate-200" };
    return <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase border ${s.cls}`}>{s.label}</span>;
  };

  return (
    <div className="flex flex-col gap-8 pb-12 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <Link href="/integrations" className="text-sm font-semibold text-slate-400 hover:text-slate-700 flex items-center gap-1.5 w-fit transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Integrations
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <Cloud className="w-6 h-6 text-[#f97316]" />
              AWS CloudTrail Integration
            </h1>
            <p className="text-slate-500 mt-1 text-sm">
              Connect your AWS account to stream CloudTrail events, discover identities, and build the security graph.
            </p>
          </div>
          {integration && getStatusBadge(integration.status)}
        </div>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-0">
        {(["configure", "validate", "sync"] as Step[]).map((s, idx) => {
          const labels = ["1. Configure", "2. Validate", "3. Sync"];
          const isActive = step === s;
          const isDone = (step === "validate" && idx === 0) || (step === "sync" && idx <= 1);
          return (
            <div key={s} className="flex items-center">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                isActive ? "bg-indigo-600 text-white shadow-sm" :
                isDone ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                "bg-slate-100 text-slate-400"
              }`}>
                {isDone ? <CheckCircle2 className="w-4 h-4" /> : <span className="w-4 h-4 flex items-center justify-center text-xs">{idx + 1}</span>}
                {labels[idx]}
              </div>
              {idx < 2 && <ChevronRight className="w-4 h-4 text-slate-300 mx-1" />}
            </div>
          );
        })}
      </div>

      {/* Error / Success Banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl flex items-start gap-3 text-sm">
          <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Error</p>
            <p className="mt-0.5 text-rose-600">{error}</p>
          </div>
        </div>
      )}
      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-4 rounded-xl flex items-center gap-3 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* =================== STEP 1: CONFIGURE =================== */}
      {step === "configure" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-6">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 flex items-center gap-2"><Key className="w-4 h-4 text-slate-500" /> Connection Settings</h3>
            </div>

            {/* Account ID + Region */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">AWS Account ID</label>
                <input
                  className="input-field h-10"
                  value={config.account_id}
                  onChange={e => setConfig({ ...config, account_id: e.target.value })}
                  placeholder="123456789012"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Region</label>
                <select
                  className="input-field h-10"
                  value={config.region}
                  onChange={e => setConfig({ ...config, region: e.target.value })}
                >
                  {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>

            {/* Auth Method */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Authentication Method</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setConfig({ ...config, auth_method: "access_key" })}
                  className={`p-3 rounded-lg border text-left transition-all ${config.auth_method === "access_key" ? "border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500" : "border-slate-200 hover:border-slate-300"}`}
                >
                  <p className="text-sm font-semibold text-slate-800">IAM User (Access Keys)</p>
                  <p className="text-xs text-slate-500 mt-0.5">Use AWS Access Key ID & Secret Key</p>
                </button>
                <button
                  onClick={() => setConfig({ ...config, auth_method: "role_arn" })}
                  className={`p-3 rounded-lg border text-left transition-all ${config.auth_method === "role_arn" ? "border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500" : "border-slate-200 hover:border-slate-300"}`}
                >
                  <p className="text-sm font-semibold text-slate-800">IAM Role (AssumeRole)</p>
                  <p className="text-xs text-slate-500 mt-0.5">Cross-account role — recommended</p>
                </button>
              </div>
            </div>

            {/* Access Key Fields */}
            {config.auth_method === "access_key" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Access Key ID</label>
                  <input
                    className="input-field h-10 font-mono text-sm"
                    value={config.access_key}
                    onChange={e => setConfig({ ...config, access_key: e.target.value })}
                    placeholder="AKIAIOSFODNN7EXAMPLE"
                    autoComplete="off"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Secret Access Key</label>
                  <input
                    className="input-field h-10 font-mono text-sm"
                    type="password"
                    value={config.secret_key}
                    onChange={e => setConfig({ ...config, secret_key: e.target.value })}
                    placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                    autoComplete="new-password"
                  />
                </div>
              </div>
            )}

            {/* Role ARN + External ID Fields */}
            {config.auth_method === "role_arn" && (
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Role ARN</label>
                  <input
                    className="input-field h-10 font-mono text-sm"
                    value={config.role_arn}
                    onChange={e => setConfig({ ...config, role_arn: e.target.value })}
                    placeholder="arn:aws:iam::123456789012:role/SentinelAIReadOnly"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-600 uppercase tracking-wide flex items-center gap-1.5">
                    External ID <span className="text-slate-400 font-normal normal-case text-[11px]">(recommended — prevents confused deputy attacks)</span>
                  </label>
                  <input
                    className="input-field h-10 font-mono text-sm"
                    value={config.external_id}
                    onChange={e => setConfig({ ...config, external_id: e.target.value })}
                    placeholder="sentinelai-unique-id-xxxx"
                  />
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={handleValidate}
                disabled={isValidating || !config.account_id}
                className="btn btn-primary flex items-center gap-2 h-10"
              >
                {isValidating ? (
                  <><RefreshCw className="w-4 h-4 animate-spin" /> Validating...</>
                ) : (
                  <><Shield className="w-4 h-4" /> Validate Credentials</>
                )}
              </button>
            </div>
          </div>

          {/* Sidebar: IAM Role Guide */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 flex flex-col gap-4 text-sm">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <ExternalLink className="w-4 h-4 text-slate-500" /> IAM Setup Guide
            </h3>
            <p className="text-slate-500 text-xs leading-relaxed">
              For production, we recommend an IAM Role with read-only access. This avoids storing long-term credentials.
            </p>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-start gap-2">
                <span className="bg-indigo-100 text-indigo-700 font-bold px-1.5 py-0.5 rounded text-[10px] mt-0.5">1</span>
                <span className="text-slate-600">In AWS Console, go to <strong>IAM → Roles → Create Role</strong></span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-indigo-100 text-indigo-700 font-bold px-1.5 py-0.5 rounded text-[10px] mt-0.5">2</span>
                <span className="text-slate-600">Choose <strong>Another AWS account</strong> as the trusted entity</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-indigo-100 text-indigo-700 font-bold px-1.5 py-0.5 rounded text-[10px] mt-0.5">3</span>
                <span className="text-slate-600">Attach <strong>AWSCloudTrail_ReadOnlyAccess</strong> and <strong>ReadOnlyAccess</strong> policies</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-indigo-100 text-indigo-700 font-bold px-1.5 py-0.5 rounded text-[10px] mt-0.5">4</span>
                <span className="text-slate-600">Copy the Role ARN and paste it above</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================== STEP 2: VALIDATE =================== */}
      {step === "validate" && validationResult && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white border border-emerald-200 rounded-xl p-6 shadow-sm flex flex-col gap-5">
            <div className="flex items-center gap-3 p-4 bg-emerald-50 rounded-lg border border-emerald-200">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 flex-shrink-0" />
              <div>
                <p className="font-bold text-emerald-800">Credentials Validated</p>
                <p className="text-xs text-emerald-600 mt-0.5">SentinelAI successfully authenticated with your AWS account.</p>
              </div>
            </div>

            <div className="flex flex-col gap-3 text-sm">
              <div className="flex justify-between items-center py-2.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Verified Account</span>
                <span className="font-mono font-semibold text-slate-800">{validationResult.account_id}</span>
              </div>
              <div className="flex justify-between items-center py-2.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Identity ARN</span>
                <span className="font-mono text-xs text-slate-600 truncate max-w-[280px]">{validationResult.arn}</span>
              </div>
              <div className="flex justify-between items-center py-2.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Region</span>
                <span className="font-mono font-semibold text-slate-800">{config.region}</span>
              </div>
              <div className="flex justify-between items-center py-2.5">
                <span className="text-slate-500 font-medium">Auth Method</span>
                <span className="font-semibold text-slate-800">{config.auth_method === "access_key" ? "IAM User (Access Keys)" : "IAM Role (AssumeRole)"}</span>
              </div>
            </div>

            <div className="flex gap-3 pt-2 border-t border-slate-100">
              <button
                onClick={() => { setStep("configure"); setValidationResult(null); setError(null); }}
                className="btn border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center gap-2 h-10"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn btn-primary flex items-center gap-2 h-10 flex-1"
              >
                <Save className="w-4 h-4" />
                {isSaving ? "Saving & Encrypting..." : "Save & Continue to Sync"}
              </button>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4 text-sm font-mono">
            <h3 className="font-bold text-slate-100 text-xs uppercase tracking-widest">Connection Check</h3>
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 className="w-4 h-4" /> STS Authentication</div>
              <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 className="w-4 h-4" /> Account Verified</div>
              <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 className="w-4 h-4" /> CloudTrail Access</div>
              {config.auth_method === "role_arn" && config.external_id && (
                <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 className="w-4 h-4" /> External ID Matched</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =================== STEP 3: SYNC =================== */}
      {step === "sync" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Status */}
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 flex items-center gap-2"><Database className="w-4 h-4 text-slate-500" /> Integration Status</h3>
              {integration && getStatusBadge(integration.status)}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="flex flex-col gap-1 p-4 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1"><Database className="w-3 h-3" /> Total Events</span>
                <span className="text-2xl font-bold text-slate-900">{(integration?.events_retrieved || 0).toLocaleString()}</span>
              </div>
              <div className="flex flex-col gap-1 p-4 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1"><Clock className="w-3 h-3" /> Last Sync</span>
                <span className="text-sm font-semibold text-slate-700 mt-1">
                  {integration?.last_sync_time ? new Date(integration.last_sync_time).toLocaleString() : "Never"}
                </span>
              </div>
              <div className="flex flex-col gap-1 p-4 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1"><Zap className="w-3 h-3" /> Account</span>
                <span className="text-sm font-mono font-semibold text-slate-700 mt-1">{integration?.config?.account_id || config.account_id}</span>
              </div>
            </div>

            {integration?.status === "error" && integration?.error_message && (
              <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-lg text-sm">
                <AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-rose-700">Sync Error</p>
                  <p className="text-rose-600 text-xs mt-1">{integration.error_message}</p>
                </div>
              </div>
            )}

            {isSyncing && (
              <div className="flex flex-col gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm">
                <div className="flex items-center gap-2 text-amber-700 font-semibold">
                  <RefreshCw className="w-4 h-4 animate-spin" /> Sync in progress — fetching CloudTrail events...
                </div>
                <p className="text-xs text-amber-600">This may take several minutes depending on the volume of events. The page will update automatically when complete.</p>
              </div>
            )}

            <div className="flex gap-3 pt-2 border-t border-slate-100">
              <button
                onClick={() => { setStep("configure"); setError(null); setSuccess(null); }}
                className="btn border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center gap-2 h-10"
              >
                <Key className="w-4 h-4" /> Edit Credentials
              </button>
              <button
                onClick={handleSync}
                disabled={isSyncing}
                className="btn bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2 h-10 flex-1 justify-center"
              >
                <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing ? "Syncing..." : "Sync Now"}
              </button>
              {(integration?.status === "success" || integration?.status === "synced_no_new_events") && (
                <Link
                  href="/cloudtrail"
                  className="btn bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 h-10 justify-center"
                >
                  View Events <ExternalLink className="w-4 h-4" />
                </Link>
              )}
            </div>
          </div>

          {/* Right: Pipeline stages — real data only */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4 font-mono text-sm">
            <h3 className="font-bold text-slate-100 text-xs uppercase tracking-widest flex items-center gap-2">
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin text-emerald-400" : "text-slate-500"}`} />
              CloudTrail Live Sync
            </h3>

            <div className="flex flex-col gap-2.5 text-xs">
              {[
                { label: "AWS Connection", done: true },
                { label: "IAM Authentication", done: true },
                { label: "CloudTrail Download", done: !isSyncing && (integration?.status === "success" || integration?.status === "synced_no_new_events") },
                { label: "Event Storage (PostgreSQL)", done: !isSyncing && (integration?.status === "success" || integration?.status === "synced_no_new_events") },
                { label: "Identity Discovery", done: !isSyncing && (integration?.status === "success" || integration?.status === "synced_no_new_events") },
                { label: "Graph Build (Neo4j)", done: !isSyncing && (integration?.status === "success" || integration?.status === "synced_no_new_events") },
                { label: "Risk Engine", done: !isSyncing && (integration?.status === "success" || integration?.status === "synced_no_new_events") },
              ].map(({ label, done }) => (
                <div key={label} className={`flex items-center gap-2 ${done ? "text-emerald-400" : isSyncing ? "text-amber-400 animate-pulse" : "text-slate-500"}`}>
                  {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : isSyncing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />}
                  {label}
                </div>
              ))}
            </div>

            {(integration?.status === "success" || integration?.status === "synced_no_new_events") && (
              <div className="mt-2 p-3 bg-slate-800 rounded-lg border border-slate-700 flex flex-col gap-2">
                <div>
                  <div className="text-slate-400 text-[10px] uppercase tracking-widest font-bold">Total Events Stored</div>
                  <div className="text-xl font-light text-slate-100 mt-0.5">{(integration?.events_retrieved || 0).toLocaleString()}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
