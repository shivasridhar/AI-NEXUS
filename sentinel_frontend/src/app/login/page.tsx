"use client";

import { motion } from "framer-motion";
import { ShieldCheck, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import Script from "next/script";
import api from "@/lib/api";
import { useGlobalStore } from "@/lib/store";

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const setCurrentWorkspaceId = useGlobalStore((state) => state.setCurrentWorkspaceId);
  const setUserRole = useGlobalStore((state) => state.setUserRole);
  const setUserFullName = useGlobalStore((state) => state.setUserFullName);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    try {
      // Fast API expects standard json body in our implementation
      const res = await api.post('/auth/login', { email, password });
      if (res.access_token) {
        localStorage.setItem('auth-storage', JSON.stringify({ state: { token: res.access_token } }));
        // Fetch workspace
        const me = await api.get('/auth/me');
        if (me.workspace && me.workspace.id) {
          setCurrentWorkspaceId(me.workspace.id);
        }
        if (me.user) {
          setUserRole(me.user.role || 'viewer');
          setUserFullName(me.user.full_name || 'User');
        }
        window.location.href = "/dashboard";
      }
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
      setIsLoading(false);
    }
  };

  const handleGoogleCredentialResponse = async (response: any) => {
    setIsLoading(true);
    setError("");
    try {
      const res = await api.post('/auth/google', { credential: response.credential });
      if (res.access_token) {
        localStorage.setItem('auth-storage', JSON.stringify({ state: { token: res.access_token } }));
        const me = await api.get('/auth/me');
        if (me.workspace && me.workspace.id) {
          setCurrentWorkspaceId(me.workspace.id);
        }
        if (me.user) {
          setUserRole(me.user.role || 'viewer');
          setUserFullName(me.user.full_name || 'User');
        }
        window.location.href = "/dashboard";
      }
    } catch (err: any) {
      setError(err.message || "Google Authentication failed");
      setIsLoading(false);
    }
  };

  const triggerGoogleAuth = () => {
    // Deprecated: Google Identity Services blocks programmatic clicks on their iframe.
    // The official button is now rendered directly.
  };

  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const isGoogleConfigured = googleClientId && !googleClientId.includes('your-google-client-id') && !googleClientId.includes('<MY_REAL_CLIENT_ID>');

  if (!isGoogleConfigured) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-50">
        <div className="bg-red-50 text-red-600 p-6 rounded-xl border border-red-200 max-w-md">
          <h2 className="text-lg font-bold mb-2">Developer Configuration Error</h2>
          <p className="text-sm">
            Google Authentication is not configured. Please set your real <strong>NEXT_PUBLIC_GOOGLE_CLIENT_ID</strong> in the <code>.env.local</code> file.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center relative z-10 p-6 bg-slate-50">
      <Script
        src="https://accounts.google.com/gsi/client"
        onLoad={() => {
          // @ts-ignore
          window.google.accounts.id.initialize({
            client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
            callback: handleGoogleCredentialResponse,
          });
          // @ts-ignore
          window.google.accounts.id.renderButton(
            document.getElementById("google-login-button-container"),
            { theme: "outline", size: "large", type: "standard", width: "400" }
          );
        }}
      />
      
      {/* Return to Home Link */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="absolute top-8 left-8"
      >
        <Link 
          href="/"
          className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors font-semibold text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
      </motion.div>

      {/* Login Card Container */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.98, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-[440px] p-8 md:p-10 rounded-[24px] flex flex-col bg-white border border-slate-200 shadow-xl"
      >
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-4 shadow-sm">
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
          </div>
          <h1 className="font-[family-name:var(--font-jakarta)] text-2xl font-bold text-slate-900 mb-2">
            Welcome back
          </h1>
          <p className="text-slate-500 text-sm">
            Sign in to your SentinelAI command center.
          </p>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-6">
          {error && <div className="text-red-500 text-sm font-semibold">{error}</div>}
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Email</label>
            <input 
              type="email" 
              required
              placeholder="name@company.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field h-11"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between ml-1">
              <label className="text-slate-700 text-sm font-semibold">Password</label>
              <a href="#" className="text-indigo-600 hover:text-indigo-700 text-xs font-semibold transition-colors">
                Forgot password?
              </a>
            </div>
            <input 
              type="password" 
              required
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field h-11"
            />
          </div>
          
          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full mt-2 h-11 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center shadow-md shadow-indigo-100"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1 h-px bg-slate-200" />
          <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Or continue with</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>

        {/* SSO & Social */}
        <div className="flex flex-col gap-3 mb-6">
          <button type="button" className="w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors">
            Sign in with SSO / SAML
          </button>
          
          <div className="relative w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors overflow-hidden">
            {/* Custom UI Button Text */}
            <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z" />
            </svg>
            <span>Continue with Google</span>
            {/* Invisible Google Button Overlay */}
            <div 
              id="google-login-button-container" 
              className="absolute inset-0 w-full h-full opacity-[0.01] cursor-pointer"
              style={{ top: 0, left: 0 }}
            ></div>
          </div>
          <button type="button" className="w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors">
            <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            <span>Continue with GitHub</span>
          </button>
        </div>

        {/* Footer */}
        <div className="text-center">
          <span className="text-slate-500 text-sm">Don&apos;t have an account? </span>
          <Link href="/signup" className="text-indigo-600 hover:text-indigo-700 text-sm font-semibold transition-colors">
            Start Free Trial
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
