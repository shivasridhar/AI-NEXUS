"use client";

import { useState } from "react";
import { Cloud, Plus } from "lucide-react";
import { useIntegrations } from "@/lib/queries/stage1";
import { IntegrationResponse } from "@/types/stage1";
import { ConnectorCard } from "./components/ConnectorCard";
import { ConnectorConfigModal } from "./components/ConnectorConfigModal";

export default function IntegrationsPage() {
  const { data: integrations = [], isLoading, error, refetch } = useIntegrations();
  
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<IntegrationResponse | null>(null);

  const handleConfigure = (connector: IntegrationResponse) => {
    setSelectedConnector(connector);
    setIsConfigModalOpen(true);
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-4 shadow-sm animate-pulse h-48">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-slate-200 rounded-lg"></div>
                <div className="h-4 bg-slate-200 rounded w-32"></div>
              </div>
              <div className="mt-4 space-y-2">
                <div className="h-3 bg-slate-100 rounded w-full"></div>
                <div className="h-3 bg-slate-100 rounded w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-8 flex flex-col items-center justify-center text-center">
          <p className="text-rose-700 font-semibold mb-4">Failed to load integrations</p>
          <button 
            onClick={() => refetch()}
            className="btn bg-rose-600 text-white hover:bg-rose-700 py-2 px-4"
          >
            Retry
          </button>
        </div>
      );
    }

    if (integrations.length === 0) {
      return (
        <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center">
          <Cloud className="w-12 h-12 text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-700 mb-2">No integrations found</h3>
          <p className="text-sm text-slate-500 mb-6">Connect your cloud environments and security tools to start monitoring.</p>
          <button className="btn btn-primary flex items-center gap-2" disabled>
            <Plus className="w-4 h-4" />
            Add Integration
          </button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((connector) => (
          <ConnectorCard 
            key={connector.provider} 
            connector={connector} 
            onConfigure={handleConfigure}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <Cloud className="w-6 h-6 text-indigo-600" />
            Connector Management
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Manage live cloud integrations and security data sources to automatically ingest and analyze events.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => refetch()}
            disabled={isLoading}
            className="btn border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 py-2 px-4 disabled:opacity-50"
          >
            Refresh Status
          </button>
        </div>
      </div>

      {/* Main Content */}
      {renderContent()}

      {/* Configuration Modal */}
      <ConnectorConfigModal 
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        connector={selectedConnector}
      />
    </div>
  );
}
