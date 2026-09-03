"use client";

import { useState } from "react";
import { Bell, Search, MessageSquare, Settings, ShieldCheck, ShieldAlert, Sparkles, GitBranch, RefreshCw, HelpCircle, LogOut } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useNotifications } from "@/lib/queries";
import { useGlobalStore } from "@/lib/store";

export default function TopNav() {
  const [showNotifications, setShowNotifications] = useState(false);
  const { data: notifications = [], isLoading } = useNotifications();
  const userFullName = useGlobalStore((state) => state.userFullName);
  const userRole = useGlobalStore((state) => state.userRole);
  const initials = userFullName
    ? userFullName.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U';
  
  const unreadCount = notifications.filter((n: any) => !n.read).length;

  const renderIcon = (type: string) => {
    switch (type) {
      case "CRITICAL": return <ShieldAlert className="w-4 h-4 text-rose-600" />;
      case "PATH": return <GitBranch className="w-4 h-4 text-amber-600" />;
      case "COPILOT": return <Sparkles className="w-4 h-4 text-indigo-600" />;
      default: return <RefreshCw className="w-4 h-4 text-emerald-600" />;
    }
  };

  return (
    <header className="h-[70px] z-40 flex items-center justify-between px-6 mb-4 bg-white border border-slate-200 rounded-2xl shadow-sm relative">
      <div className="flex items-center gap-6">
        <div className="relative flex items-center">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Quick search by identity or risk..."
            className="h-10 w-64 md:w-80 rounded-xl pl-9 pr-4 text-xs text-slate-800 placeholder:text-slate-400 bg-slate-50 border border-slate-200 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600/10 transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Notification Bell with interactive dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative w-10 h-10 rounded-xl flex items-center justify-center bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 transition-colors shadow-sm"
          >
            <Bell className="w-4.5 h-4.5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-rose-600 text-white text-[9px] font-extrabold w-5 h-5 rounded-full flex items-center justify-center border-2 border-white animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          <AnimatePresence>
            {showNotifications && (
              <>
                {/* Backdrop Clicker */}
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowNotifications(false)}
                />
                
                {/* Dropdown Container */}
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden"
                >
                  <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800">Notification Center</span>
                    <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                      {unreadCount} UNREAD
                    </span>
                  </div>
                  
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {isLoading ? (
                      <div className="p-4 text-xs text-center text-slate-500">Loading...</div>
                    ) : notifications.length === 0 ? (
                      <div className="p-4 text-xs text-center text-slate-500">No new notifications.</div>
                    ) : (
                      notifications.map((notif: any) => (
                        <div 
                          key={notif.id} 
                          className={`p-3.5 hover:bg-slate-50 transition-colors flex gap-3 items-start ${
                            !notif.read ? "bg-indigo-50/20" : ""
                          }`}
                        >
                          <div className="p-1.5 bg-slate-100 rounded-lg mt-0.5">
                            {renderIcon(notif.type)}
                          </div>
                          <div className="flex-1 flex flex-col gap-0.5">
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-bold text-slate-900 leading-tight truncate w-36">{notif.title}</span>
                              <span className="text-[9px] text-slate-400 font-mono">{new Date(notif.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                            </div>
                            <p className="text-xs text-slate-500 leading-normal line-clamp-2">{notif.desc}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="p-3 border-t border-slate-100 bg-slate-50 text-center">
                    <button 
                      onClick={() => setShowNotifications(false)}
                      className="text-[11px] font-bold text-indigo-600 hover:text-indigo-700"
                    >
                      Close
                    </button>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>

        {/* User Profile Glass Capsule */}
        <div className="h-10 pl-1.5 pr-3 rounded-xl flex items-center gap-2.5 bg-slate-50 border border-slate-200 shadow-sm ml-1">
          <div className="relative">
            <div className="w-7.5 h-7.5 rounded-lg bg-indigo-600 flex items-center justify-center overflow-hidden text-white font-bold text-xs">
              {initials}
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-[11px] font-bold text-slate-800 leading-tight">{userFullName || 'User'}</span>
            <span className="text-[9px] font-medium text-slate-400 capitalize">{userRole || 'viewer'}</span>
          </div>
        </div>
        
        {/* Sign Out Button */}
        <button
          onClick={() => {
            localStorage.removeItem('auth-storage');
            window.location.href = '/login';
          }}
          title="Sign Out"
          className="w-10 h-10 rounded-xl flex items-center justify-center bg-slate-50 hover:bg-rose-50 hover:text-rose-600 border border-slate-200 text-slate-600 transition-colors shadow-sm ml-2"
        >
          <LogOut className="w-4.5 h-4.5" />
        </button>
      </div>
    </header>
  );
}
