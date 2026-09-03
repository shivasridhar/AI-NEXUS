export interface AttackPathGraph {
  nodes: Array<{ id: string; type?: string; label?: string; data: any; position?: any }>;
  edges: Array<{ id: string; source: string; target: string; label?: string; type?: string }>;
}

export interface AIInvestigationRequest {
  identity_id: string;
  query?: string;
}

export interface AIInvestigationResponse {
  success?: boolean;
  code?: string;
  message?: string;
  investigation_id?: string;
  identity_id?: string;
  executive_summary?: string;
  risk_assessment?: string;
  attack_path_analysis?: string;
  findings?: string[];
  recommendations?: string[];
  confidence_score?: number;
  analyzed_at?: string;
}

