"use client";

import { motion } from "framer-motion";
import { ShieldCheck, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import Script from "next/script";
import api from "@/lib/api";
import { useGlobalStore } from "@/lib/store";

export default function SignupPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const setCurrentWorkspaceId = useGlobalStore((state) => state.setCurrentWorkspaceId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const payload = {
        email,
        password,
        full_name: fullName,
        organization_name: companyName,
        workspace_name: "Default Workspace"
      };
      const res = await api.post('/auth/register', payload);
      if (res.access_token) {
        localStorage.setItem('auth-storage', JSON.stringify({ state: { token: res.access_token } }));
        const me = await api.get('/auth/me');
        if (me.workspace && me.workspace.id) {
          setCurrentWorkspaceId(me.workspace.id);
        }
        window.location.href = "/dashboard";
      }
    } catch (err: any) {
      setError(err.message || "Signup failed");
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

      {/* Signup Card Container */}
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
            Create your account
          </h1>
          <p className="text-slate-500 text-sm">
            Start protecting machine identities in minutes.
          </p>
        </div>

        {/* Signup Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-6">
          {error && <div className="text-red-500 text-sm font-semibold">{error}</div>}
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Company Name</label>
            <input 
              type="text" 
              required
              placeholder="Acme Corporation" 
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="input-field h-11"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Full Name</label>
            <input 
              type="text" 
              required
              placeholder="Alex Smith" 
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="input-field h-11"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Work Email</label>
            <input 
              type="email" 
              required
              placeholder="alex@company.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field h-11"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Password</label>
            <input 
              type="password" 
              required
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field h-11"
            />
            <span className="text-[10px] text-slate-500 ml-1">Must be at least 12 characters and include upper, lower, number, and special character.</span>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-slate-700 text-sm font-semibold ml-1">Confirm Password</label>
            <input 
              type="password" 
              required
              placeholder="••••••••" 
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-field h-11"
            />
          </div>

          <div className="flex items-start gap-2.5 ml-1 mt-1">
            <input 
              type="checkbox" 
              required 
              id="terms"
              className="mt-1 accent-indigo-600"
            />
            <label htmlFor="terms" className="text-xs text-slate-500 leading-normal">
              I agree to the{" "}
              <a href="#" className="text-indigo-600 hover:underline">Terms of Service</a>
              {" "}and{" "}
              <a href="#" className="text-indigo-600 hover:underline">Privacy Policy</a>.
            </label>
          </div>
          
          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full mt-2 h-11 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center shadow-md shadow-indigo-100"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Start Free Trial"
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1 h-px bg-slate-200" />
          <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Or continue with</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>

        {/* Social Options */}
        <div className="flex flex-col gap-3 mb-6">
          <div className="relative w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors overflow-hidden">
            {/* Custom UI Button Text */}
            <span>Continue with Google</span>
            {/* Invisible Google Button Overlay */}
            <div 
              id="google-login-button-container" 
              className="absolute inset-0 w-full h-full opacity-[0.01] cursor-pointer"
              style={{ top: 0, left: 0 }}
            ></div>
          </div>
          <button type="button" className="w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors">
            Continue with Microsoft
          </button>
          <button type="button" disabled className="w-full h-11 flex items-center justify-center gap-2 rounded-xl text-sm font-semibold border border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed opacity-60">
            Sign up with SSO (Coming Soon)
          </button>
        </div>

        {/* Footer */}
        <div className="text-center">
          <span className="text-slate-500 text-sm">Already have an account? </span>
          <Link href="/login" className="text-indigo-600 hover:text-indigo-700 text-sm font-semibold transition-colors">
            Sign In
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
