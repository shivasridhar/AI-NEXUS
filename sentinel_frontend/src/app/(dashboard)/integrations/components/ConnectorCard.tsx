"use client";

import { IntegrationResponse } from "@/types/stage1";
import { STAGE1_CONFIG } from "@/lib/stage1.config";
import { 
  Cloud, 
  Server, 
  ShieldCheck, 
  Network,
  Activity,
  AlertTriangle
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface ConnectorCardProps {
  connector: IntegrationResponse;
  onConfigure: (connector: IntegrationResponse) => void;
}

export function ConnectorCard({ connector, onConfigure }: ConnectorCardProps) {
  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case "aws":
      case "azure":
        return <Cloud className="w-5 h-5" />;
      case "wazuh":
      case "crowdstrike":
        return <ShieldCheck className="w-5 h-5" />;
      case "suricata":
        return <Network className="w-5 h-5" />;
      case "openvas":
        return <Activity className="w-5 h-5" />;
      default:
        return <Server className="w-5 h-5" />;
    }
  };

  const statusClasses = STAGE1_CONFIG.UI_MAPS.CONNECTOR_STATUS_COLORS[connector.status] || "bg-slate-100 text-slate-700";
  const statusLabel = STAGE1_CONFIG.UI_MAPS.CONNECTOR_STATUS_LABELS[connector.status] || connector.status;
  const displayName = STAGE1_CONFIG.UI_MAPS.CONNECTOR_NAMES[connector.provider] || connector.name || connector.provider;

  // Separate background and text color for icon container
  const iconBgMap: Record<string, string> = {
    available: "bg-slate-100 text-slate-600",
    coming_soon: "bg-slate-50 text-slate-400",
    configured: "bg-indigo-50 text-indigo-600",
    syncing: "bg-blue-50 text-blue-600",
    success: "bg-emerald-50 text-emerald-600",
    synced_no_new_events: "bg-amber-50 text-amber-600",
    error: "bg-rose-50 text-rose-600",
  };
  const iconColors = iconBgMap[connector.status] || "bg-slate-100 text-slate-600";

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-4 shadow-sm hover:border-slate-300 transition-all">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-lg border border-slate-200 ${iconColors}`}>
            {getProviderIcon(connector.provider)}
          </div>
          <h3 className="font-bold text-slate-900 text-sm">{displayName}</h3>
        </div>
        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase border border-slate-200 ${statusClasses}`}>
          {statusLabel}
        </span>
      </div>

      <div className="text-xs text-slate-500 h-10 flex flex-col justify-center">
        {connector.status === 'coming_soon' && (
          <p>This integration is coming soon.</p>
        )}
        {connector.status === 'available' && (
          <p>Ready to be configured.</p>
        )}
        {connector.status !== 'coming_soon' && connector.status !== 'available' && (
          <div className="flex flex-col gap-1">
            <div className="flex justify-between">
              <span className="font-semibold text-slate-700">Events Retrieved:</span> 
              <span>{connector.events_retrieved?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-semibold text-slate-700">Last Sync:</span> 
              <span>
                {connector.last_sync_time 
                  ? formatDistanceToNow(new Date(connector.last_sync_time), { addSuffix: true }) 
                  : 'Never'}
              </span>
            </div>
          </div>
        )}
      </div>
      
      {connector.status === "error" && connector.error_message && (
        <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded flex items-start gap-2 border border-rose-100">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span className="line-clamp-2" title={connector.error_message}>
            {connector.error_message}
          </span>
        </div>
      )}

      <div className="flex items-center justify-end pt-3 border-t border-slate-100 mt-auto">
        {connector.status !== 'coming_soon' ? (
          <button 
            onClick={() => onConfigure(connector)}
            className={`btn text-xs py-1.5 px-3 transition-colors ${
              connector.status === 'available' 
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm' 
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {connector.status === 'available' ? 'Configure' : 'Manage'}
          </button>
        ) : (
          <button disabled className="btn border border-slate-200 bg-slate-50 text-slate-400 text-xs py-1.5 px-3 cursor-not-allowed">
            Coming Soon
          </button>
        )}
      </div>
    </div>
  );
}
