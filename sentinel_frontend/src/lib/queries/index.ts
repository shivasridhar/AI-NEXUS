import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api";
import { DashboardSummary, Identity, RiskFinding } from "../../types";
import { AttackPathGraph, AIInvestigationRequest, AIInvestigationResponse } from "../../types/canvas";

export const useDashboardSummary = () => {
  return useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: async (): Promise<DashboardSummary> => {
      const res = await api.get('/dashboard/summary');
      return res;
    }
  });
};

export const useRecentFindings = () => {
  return useQuery({
    queryKey: ['recentFindings'],
    queryFn: async (): Promise<RiskFinding[]> => {
      const res = await api.get('/dashboard/recent-findings');
      return res;
    }
  });
};

export const useFindingDetails = (findingId: string) => {
  return useQuery({
    queryKey: ['findingDetails', findingId],
    queryFn: async (): Promise<any> => {
      const res = await api.get(`/findings/${findingId}`);
      return res;
    },
    enabled: !!findingId,
  });
};

export const useRecentEvents = () => {
  return useQuery({
    queryKey: ['recentEvents'],
    queryFn: async (): Promise<any[]> => {
      const res = await api.get('/dashboard/recent-events');
      return res;
    },
    refetchInterval: 5000 // Poll every 5s for live updates
  });
};

export const useTopAttackPaths = () => {
  return useQuery({
    queryKey: ['topAttackPaths'],
    queryFn: async (): Promise<any[]> => {
      const res = await api.get('/dashboard/top-attack-paths');
      return res;
    }
  });
};

export const useIdentities = () => {
  return useQuery({
    queryKey: ['identities'],
    queryFn: async (): Promise<Identity[]> => {
      const res = await api.get('/identities');
      return res.sort((a: any, b: any) => b.risk_score - a.risk_score);
    }
  });
};

export const useGetAttackPath = (identityId: string) => {
  return useQuery({
    queryKey: ['attackPath', identityId],
    queryFn: async (): Promise<AttackPathGraph> => {
      const res = await api.get(`/identities/${identityId}/attack-path`);
      return res;
    },
    enabled: !!identityId,
  });
};

export const useAiInvestigate = () => {
  return useMutation({
    mutationFn: async (req: AIInvestigationRequest): Promise<AIInvestigationResponse> => {
      const res = await api.post('/ai/investigate', req);
      return res;
    }
  });
};

export const useAnalytics = () => {
  return useQuery({
    queryKey: ['analyticsDashboard'],
    queryFn: async (): Promise<any> => {
      const res = await api.get('/analytics/dashboard');
      return res;
    }
  });
};

export const useNotifications = () => {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: async (): Promise<any[]> => {
      const res = await api.get('/notifications');
      return res;
    },
    refetchInterval: 10000 // Poll every 10s
  });
};

export const useOrganization = () => {
  return useQuery({
    queryKey: ['organization'],
    queryFn: async (): Promise<any> => {
      const res = await api.get('/organizations/me');
      return res;
    }
  });
};

export const useUploadCloudTrail = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      // Let the browser handle the Content-Type boundary for FormData
      const res = await api.post('/ingestion/upload', formData);
      return res;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] });
      queryClient.invalidateQueries({ queryKey: ['identities'] });
      queryClient.invalidateQueries({ queryKey: ['recentFindings'] });
      queryClient.invalidateQueries({ queryKey: ['recentEvents'] });
      queryClient.invalidateQueries({ queryKey: ['topAttackPaths'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsDashboard'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    }
  });
};

export const useAuditLogs = (skip: number = 0, limit: number = 100) => {
  return useQuery({
    queryKey: ['auditLogs', skip, limit],
    queryFn: async (): Promise<{data: any[]}> => {
      return await api.get(`/audit-logs?skip=${skip}&limit=${limit}`);
    }
  });
};

export const useAuditStatistics = () => {
  return useQuery({
    queryKey: ['auditStatistics'],
    queryFn: async (): Promise<any> => {
      return await api.get('/audit-logs/statistics');
    }
  });
};

export const useReports = (skip: number = 0, limit: number = 100) => {
  return useQuery({
    queryKey: ['reports', skip, limit],
    queryFn: async (): Promise<{data: any[]}> => {
      return await api.get(`/reports?skip=${skip}&limit=${limit}`);
    },
    refetchInterval: (query) => {
      // Poll every 3 seconds if any report is in a non-terminal state
      const data = query.state.data as {data: any[]} | undefined;
      const activeStates = ['QUEUED', 'GENERATING', 'VALIDATING', 'RENDERING', 'UPLOADING', 'RETRYING'];
      const isGenerating = data?.data?.some(r => activeStates.includes(r.status));
      return isGenerating ? 3000 : false;
    }
  });
};

export const useReportStatistics = () => {
  return useQuery({
    queryKey: ['reportStatistics'],
    queryFn: async (): Promise<any> => {
      return await api.get('/reports/statistics');
    }
  });
};

export const useGenerateReport = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (req: {name: string, report_type: string, filters: Record<string, any>}): Promise<any> => {
      return await api.post('/reports/generate', req);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      queryClient.invalidateQueries({ queryKey: ['reportStatistics'] });
    }
  });
};

// ── MITRE ATT&CK & Compliance ──────────────────────────────────────────

export const useMitreTechniques = () => {
  return useQuery({
    queryKey: ['mitreTechniques'],
    queryFn: async (): Promise<{techniques: any[], total: number}> => {
      return await api.get('/mitre/techniques');
    }
  });
};

export const useComplianceScores = () => {
  return useQuery({
    queryKey: ['complianceScores'],
    queryFn: async (): Promise<any> => {
      return await api.get('/mitre/compliance');
    }
  });
};

export const useExportReport = () => {
  return useMutation({
    mutationFn: async (req: { identity_id?: string; finding_id?: string; filename: string }): Promise<void> => {
      const { filename, ...body } = req;
      return await api.postDownload('/reports/export', body, filename);
    }
  });
};

// ── AI Conversations ──────────────────────────────────────────────────

export const useAiConversations = (identityId?: string) => {
  return useQuery({
    queryKey: ['aiConversations', identityId],
    queryFn: async (): Promise<any[]> => {
      let url = '/ai-conversations';
      if (identityId) url += `?identity_id=${identityId}`;
      return await api.get(url);
    }
  });
};

export const useCreateAiConversation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (req: { title?: string; identity_id?: string; message?: any }): Promise<any> => {
      return await api.post('/ai-conversations/', req);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aiConversations'] });
    }
  });
};

export const useUpdateAiConversation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (req: { id: string; title?: string; message?: any }): Promise<any> => {
      const { id, ...body } = req;
      return await api.put(`/ai-conversations/${id}`, body);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['aiConversations'] });
    }
  });
};

