import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type DashboardView = 'executive' | 'soc';

interface GlobalState {
  isUploading: boolean;
  setUploading: (status: boolean) => void;
  theme: 'Dark' | 'Light' | 'System';
  setTheme: (theme: 'Dark' | 'Light' | 'System') => void;
  currentWorkspaceId: string | null;
  setCurrentWorkspaceId: (id: string | null) => void;
  autoRefreshInterval: number | null;
  setAutoRefreshInterval: (interval: number | null) => void;
  dashboardView: DashboardView;
  setDashboardView: (view: DashboardView) => void;
  userRole: string | null;
  setUserRole: (role: string | null) => void;
  userFullName: string | null;
  setUserFullName: (name: string | null) => void;
}

export const useGlobalStore = create<GlobalState>()(
  persist(
    (set) => ({
      isUploading: false,
      setUploading: (status) => set({ isUploading: status }),
      theme: 'System',
      setTheme: (theme) => set({ theme }),
      currentWorkspaceId: null,
      setCurrentWorkspaceId: (id) => set({ currentWorkspaceId: id }),
      autoRefreshInterval: 5000,
      setAutoRefreshInterval: (interval) => set({ autoRefreshInterval: interval }),
      dashboardView: 'executive',
      setDashboardView: (view) => set({ dashboardView: view }),
      userRole: null,
      setUserRole: (role) => set({ userRole: role }),
      userFullName: null,
      setUserFullName: (name) => set({ userFullName: name }),
    }),
    {
      name: 'sentinel-storage',
    }
  )
);
