"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5000,
        refetchOnWindowFocus: false,
      },
    },
  }));

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const tokenStr = localStorage.getItem('auth-storage');
      const hasToken = tokenStr && tokenStr.includes('"token"');
      const isAuthPage = window.location.pathname.startsWith('/login') || window.location.pathname.startsWith('/signup') || window.location.pathname === '/';
      
      if (hasToken && isAuthPage) {
        window.location.href = '/dashboard';
      } else if (!hasToken && window.location.pathname.startsWith('/dashboard')) {
        window.location.href = '/login';
      }
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
