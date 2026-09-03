import { ConnectorSchemaField } from "@/types/stage1";

// TODO: replace with real Stage 1 implementation from teammate.
export const STAGE1_CONFIG = {
  UI_MAPS: {
    CONNECTOR_STATUS_COLORS: {
      available: "bg-slate-100 text-slate-700",
      coming_soon: "bg-slate-100 text-slate-500",
      configured: "bg-blue-100 text-blue-700",
      syncing: "bg-indigo-100 text-indigo-700",
      success: "bg-emerald-100 text-emerald-700",
      synced_no_new_events: "bg-emerald-50 text-emerald-600",
      error: "bg-rose-100 text-rose-700",
    } as Record<string, string>,
    
    CONNECTOR_STATUS_LABELS: {
      available: "Available",
      coming_soon: "Coming Soon",
      configured: "Configured",
      syncing: "Syncing...",
      success: "Synced",
      synced_no_new_events: "Synced",
      error: "Error",
    } as Record<string, string>,
    
    CONNECTOR_NAMES: {
      aws: "AWS CloudTrail",
      azure: "Azure Active Directory",
      okta: "Okta Identity",
      crowdstrike: "CrowdStrike Falcon",
      wazuh: "Wazuh SIEM",
      suricata: "Suricata IDS",
      openvas: "OpenVAS",
    } as Record<string, string>,
  },
  
  CONNECTOR_SCHEMAS: {
    aws: [
      { name: "account_id", label: "AWS Account ID", type: "text", required: true, placeholder: "123456789012" },
      { name: "region", label: "AWS Region", type: "text", required: true, defaultValue: "us-east-1" },
      { name: "auth_method", label: "Authentication Method", type: "select", required: true, defaultValue: "access_key", options: [{label: "Access Key", value: "access_key"}, {label: "IAM Role (Cross-Account)", value: "role_arn"}] },
      { name: "access_key", label: "Access Key ID", type: "text", required: false, placeholder: "AKIA..." },
      { name: "secret_key", label: "Secret Access Key", type: "password", required: false },
      { name: "role_arn", label: "Role ARN", type: "text", required: false, placeholder: "arn:aws:iam::..." },
      { name: "external_id", label: "External ID", type: "text", required: false }
    ],
    wazuh: [
      { name: "base_url", label: "Wazuh API URL", type: "text", required: true, placeholder: "https://wazuh.example.com:55000" },
      { name: "user", label: "Username", type: "text", required: true, placeholder: "wazuh-wui" },
      { name: "password", label: "Password", type: "password", required: true }
    ],
    suricata: [
      { name: "log_path", label: "Eve JSON Log Path", type: "text", required: true, placeholder: "/var/log/suricata/eve.json" },
      { name: "hostname", label: "Sensor Hostname", type: "text", required: false, placeholder: "suricata-sensor-01" }
    ],
    openvas: [
      { name: "host", label: "OpenVAS Host", type: "text", required: true, placeholder: "192.168.1.100" },
      { name: "port", label: "GMP Port", type: "number", required: true, defaultValue: 9390 },
      { name: "username", label: "GMP Username", type: "text", required: true, placeholder: "admin" },
      { name: "password", label: "GMP Password", type: "password", required: true }
    ],
    azure: [],
    okta: [],
    crowdstrike: [],
  } as Record<string, ConnectorSchemaField[]>
};
