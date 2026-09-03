"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Save } from "lucide-react";
import { IntegrationResponse, ConnectorType, ConnectorSchemaField } from "@/types/stage1";
import { STAGE1_CONFIG } from "@/lib/stage1.config";
import { useConfigureIntegration } from "@/lib/queries/stage1";

interface ConnectorConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  connector: IntegrationResponse | null;
}

export function ConnectorConfigModal({ isOpen, onClose, connector }: ConnectorConfigModalProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const { mutateAsync: configureIntegration, isPending } = useConfigureIntegration();

  // Reset form when modal opens with a new connector
  useState(() => {
    if (connector) {
      setFormData({});
      setErrorMsg(null);
    }
  });

  if (!isOpen || !connector) return null;

  const schema = STAGE1_CONFIG.CONNECTOR_SCHEMAS[connector.provider] || [];
  const displayName = STAGE1_CONFIG.UI_MAPS.CONNECTOR_NAMES[connector.provider] || connector.name;

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      await configureIntegration({ 
        provider: connector.provider, 
        config: formData 
      });
      // Assuming success if no exception is thrown
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to configure connector");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" 
            onClick={() => !isPending && onClose()}
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-[500px] bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-white">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Configure {displayName}</h2>
                <p className="text-xs text-slate-500 mt-1">Set up connection parameters and authentication.</p>
              </div>
              <button 
                onClick={() => !isPending && onClose()}
                disabled={isPending}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors disabled:opacity-50"
                aria-label="Close configuration modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
              <div className="p-6 flex flex-col gap-5 overflow-y-auto custom-scrollbar">
                
                {errorMsg && (
                  <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-100 rounded-lg">
                    {errorMsg}
                  </div>
                )}

                {schema.length === 0 ? (
                  <div className="text-sm text-slate-500 text-center py-4">
                    No configuration fields required for this connector.
                  </div>
                ) : (
                  schema.map((field: ConnectorSchemaField) => (
                    <div key={field.name} className="flex flex-col gap-1.5">
                      <label htmlFor={field.name} className="text-sm font-semibold text-slate-700">
                        {field.label} {field.required && <span className="text-rose-500">*</span>}
                      </label>
                      
                      {field.type === 'select' ? (
                        <select
                          id={field.name}
                          required={field.required}
                          value={formData[field.name] || field.defaultValue || ''}
                          onChange={(e) => handleInputChange(field.name, e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent transition-all"
                        >
                          <option value="" disabled>Select {field.label}...</option>
                          {field.options?.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          id={field.name}
                          type={field.type}
                          required={field.required}
                          placeholder={field.placeholder || (field.type === 'password' ? '••••••••' : '')}
                          value={formData[field.name] || (field.type !== 'password' ? field.defaultValue || '' : '')}
                          onChange={(e) => handleInputChange(field.name, field.type === 'number' ? Number(e.target.value) : e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent transition-all"
                        />
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 p-5 border-t border-slate-100 bg-slate-50 mt-auto">
                <button 
                  type="button"
                  onClick={() => !isPending && onClose()}
                  disabled={isPending}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-all flex items-center gap-2 disabled:opacity-80 disabled:cursor-not-allowed"
                >
                  {isPending ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
                  ) : (
                    <><Save className="w-4 h-4" /> Save Configuration</>
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
