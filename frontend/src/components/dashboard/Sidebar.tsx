"use client";

import React from "react";
import {
  LayoutDashboard,
  Film,
  UploadCloud,
  Cloud,
  ShieldCheck,
  LogOut,
  Sliders,
  HardDrive,
  UserCheck,
} from "lucide-react";
import { TenantInfo } from "@/lib/api";

export type DashboardTab = "overview" | "videos" | "upload" | "storage" | "admin";

interface SidebarProps {
  currentTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
  tenant: TenantInfo | null;
  userRole: string;
  userEmail: string;
  onLogout: () => void;
  videoCount: number;
}

export function Sidebar({
  currentTab,
  onTabChange,
  tenant,
  userRole,
  userEmail,
  onLogout,
  videoCount,
}: SidebarProps) {
  const storageLimit = tenant?.quota?.storage_bytes_limit || 5 * 1024 * 1024 * 1024;
  const storageUsed = tenant?.usage?.storage_bytes_used || 0;
  const storagePercent = Math.min(100, Math.round((storageUsed / storageLimit) * 100));

  const navItems: { id: DashboardTab; label: string; icon: any; badge?: string; adminOnly?: boolean }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "videos", label: "Video Library", icon: Film, badge: videoCount > 0 ? String(videoCount) : undefined },
    { id: "upload", label: "Upload Studio", icon: UploadCloud },
    { id: "storage", label: "Cloud Storage (BYOS)", icon: Cloud },
    { id: "admin", label: "Admin & Security", icon: Sliders, badge: "Admin", adminOnly: true },
  ];

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between shrink-0 h-screen sticky top-0 backdrop-blur-xl select-none">
      {/* Brand Header */}
      <div>
        <div className="h-16 px-5 flex items-center gap-3 border-b border-slate-800/80">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 border border-indigo-400/30 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="overflow-hidden">
            <div className="text-sm font-bold text-slate-100 truncate tracking-tight">
              AetherStream
            </div>
            <div className="text-[11px] text-indigo-400 font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Secure Studio
            </div>
          </div>
        </div>

        {/* Tenant Organization Tag */}
        <div className="px-5 py-3 bg-slate-950/40 border-b border-slate-800/60 flex items-center justify-between">
          <div className="truncate pr-2">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
              Workspace
            </div>
            <div className="text-xs font-medium text-slate-200 truncate">
              {tenant?.name || "My Organization"}
            </div>
          </div>
          <span className="text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full uppercase tracking-wider">
            {tenant?.plan_tier || "FREE"}
          </span>
        </div>

        {/* Navigation Menu */}
        <nav className="p-3 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25 font-semibold"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-md font-semibold ${
                      isActive
                        ? "bg-indigo-700 text-white"
                        : item.adminOnly
                        ? "bg-purple-950 text-purple-300 border border-purple-800/60"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer: Quota Mini-Progress & User Profile */}
      <div className="p-4 border-t border-slate-800/80 space-y-4 bg-slate-950/20">
        {/* Storage Mini-Meter */}
        <div className="bg-slate-950/60 border border-slate-800/80 p-3 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 flex items-center gap-1">
              <HardDrive className="w-3 h-3 text-indigo-400" />
              Storage Used
            </span>
            <span className="font-semibold text-slate-200">{storagePercent}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                storagePercent > 90 ? "bg-rose-500" : "bg-indigo-500"
              }`}
              style={{ width: `${storagePercent}%` }}
            />
          </div>
        </div>

        {/* User Profile Bar */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-300 shrink-0 font-bold text-xs uppercase">
              {userEmail ? userEmail.slice(0, 2) : "US"}
            </div>
            <div className="overflow-hidden">
              <div className="text-xs font-semibold text-slate-200 truncate">
                {userEmail || "Creator"}
              </div>
              <div className="text-[10px] text-slate-400 flex items-center gap-1 font-mono uppercase">
                <UserCheck className="w-2.5 h-2.5 text-emerald-400" />
                {userRole || "CREATOR"}
              </div>
            </div>
          </div>

          <button
            onClick={onLogout}
            title="Sign Out"
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
