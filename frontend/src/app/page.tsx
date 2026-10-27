"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Lock,
  ArrowRight,
  Loader2,
  HardDrive,
  Film,
  Cloud,
  CheckCircle2,
} from "lucide-react";
import { api, TenantInfo, VideoItem } from "@/lib/api";
import { Sidebar, DashboardTab } from "@/components/dashboard/Sidebar";
import { OverviewTab } from "@/components/dashboard/OverviewTab";
import { VideosTab } from "@/components/dashboard/VideosTab";
import { UploadTab } from "@/components/dashboard/UploadTab";
import { StorageTab } from "@/components/dashboard/StorageTab";
import { SecurityTab } from "@/components/dashboard/SecurityTab";
import { AdminTab } from "@/components/dashboard/AdminTab";
import { SecurePlayer } from "@/components/SecurePlayer";

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [userRole, setUserRole] = useState("ADMIN");
  const [userEmail, setUserEmail] = useState("");
  const [currentTab, setCurrentTab] = useState<DashboardTab>("overview");
  const [activeVideo, setActiveVideo] = useState<{ id: string; title: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Auth form state: "login" | "register"
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [orgName, setOrgName] = useState("Alpha Academy");
  const [email, setEmail] = useState("creator@alpha.io");
  const [password, setPassword] = useState("Password123!");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);

  useEffect(() => {
    const savedToken = api.getToken();
    if (savedToken) {
      setToken(savedToken);
      setUserRole(api.getUserRole());
      setUserEmail(api.getUserEmail());
      loadDashboardData();
    } else {
      setIsLoading(false);
    }
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const [orgData, videosData] = await Promise.all([
        api.getMyOrganization(),
        api.getVideos(),
      ]);
      setTenant(orgData);
      setVideos(videosData);
    } catch (err: any) {
      console.error(err);
      if (
        err.message?.includes("credentials") ||
        err.message?.includes("401") ||
        err.message?.includes("organization")
      ) {
        api.clearToken();
        setToken(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSubmitting(true);
    try {
      if (authMode === "register") {
        await api.register(orgName, email, password);
      } else {
        await api.login(email, password);
      }
      setToken(api.getToken());
      setUserRole(api.getUserRole());
      setUserEmail(api.getUserEmail());
      await loadDashboardData();
    } catch (err: any) {
      setAuthError(err.message || "Authentication failed");
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleLogout = () => {
    api.clearToken();
    setToken(null);
    setTenant(null);
    setVideos([]);
    setUserRole("CREATOR");
    setUserEmail("");
    setCurrentTab("overview");
  };

  // Auth Screen if unauthenticated
  if (!token) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6 bg-[#080B11] text-slate-100 relative overflow-hidden">
        {/* Subtle Background Glows */}
        <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-indigo-600/10 rounded-full blur-[128px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-purple-600/10 rounded-full blur-[128px] pointer-events-none" />

        <div className="w-full max-w-md bg-slate-900/80 border border-slate-800/90 p-8 rounded-3xl shadow-2xl backdrop-blur-xl relative z-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-white shadow-lg bg-gradient-to-tr from-indigo-600 to-indigo-500 border border-indigo-400/30 shadow-indigo-600/30">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                AetherStream Studio
              </h1>
              <p className="text-xs text-indigo-400 font-medium">
                Encrypted Video Delivery & BYOS Platform
              </p>
            </div>
          </div>

          {/* Form Mode Tabs: Sign In & Register */}
          <div className="grid grid-cols-2 p-1 bg-slate-950/80 rounded-xl mb-6 border border-slate-800/80 text-xs font-semibold">
            <button
              type="button"
              onClick={() => { setAuthMode("login"); setAuthError(null); }}
              className={`py-2 rounded-lg transition-all ${
                authMode === "login" ? "bg-indigo-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setAuthMode("register"); setAuthError(null); }}
              className={`py-2 rounded-lg transition-all ${
                authMode === "register" ? "bg-indigo-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {authMode === "register" && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Studio / Organization Name
                </label>
                <input
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="e.g. Masterclass Studio"
                  className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="creator@alpha.io"
                className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {authError && (
              <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/50 p-3 rounded-xl">
                {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={authSubmitting}
              className="w-full text-white font-semibold py-2.5 rounded-xl text-xs transition-all shadow-lg flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/25"
            >
              {authSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : authMode === "register" ? (
                "Create Free Account"
              ) : (
                "Sign In"
              )}
            </button>
          </form>


          {/* Quick Feature Highlights */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              15 GB Google Drive
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              AES-128 DRM
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Anti-Capture Lock
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              $0 Egress Forever
            </span>
          </div>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => setCurrentTab(tab)}
        tenant={tenant}
        userRole={userRole}
        userEmail={userEmail}
        onLogout={handleLogout}
        videoCount={videos.length}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <header className="h-16 px-6 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-sm font-semibold text-slate-200 capitalize">
              {currentTab === "overview" && "Dashboard Overview"}
              {currentTab === "videos" && "Video Library"}
              {currentTab === "upload" && "Upload Studio"}
              {currentTab === "storage" && "Cloud Storage & BYOS"}
              {currentTab === "admin" && "Admin & Security Console"}
            </div>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-700"></span>
            <span className="text-xs text-slate-400">{tenant?.name}</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Delivery Plane Active
            </span>
          </div>
        </header>

        {/* Tab View Content */}
        <main className="p-6 sm:p-8 flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="h-96 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-slate-400">Loading studio metrics...</p>
            </div>
          ) : (
            <>
              {currentTab === "overview" && (
                <OverviewTab
                  tenant={tenant}
                  videos={videos}
                  onNavigate={(tab) => setCurrentTab(tab)}
                  onPlayVideo={(v) => setActiveVideo({ id: v.id, title: v.title })}
                />
              )}

              {currentTab === "videos" && (
                <VideosTab
                  videos={videos}
                  onRefresh={loadDashboardData}
                  onPlayVideo={(v) => setActiveVideo({ id: v.id, title: v.title })}
                  onNavigateUpload={() => setCurrentTab("upload")}
                />
              )}

              {currentTab === "upload" && (
                <UploadTab
                  tenant={tenant}
                  onUploadSuccess={loadDashboardData}
                  onNavigateVideos={() => setCurrentTab("videos")}
                />
              )}

              {currentTab === "storage" && (
                <StorageTab onStorageUpdated={loadDashboardData} />
              )}

              {currentTab === "security" && (
                <SecurityTab />
              )}

              {currentTab === "admin" && (
                <AdminTab
                  tenant={tenant}
                  userRole={userRole}
                  userEmail={userEmail}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Secure Video Player Modal */}
      {activeVideo && (
        <SecurePlayer
          videoId={activeVideo.id}
          videoTitle={activeVideo.title}
          onClose={() => setActiveVideo(null)}
        />
      )}
    </div>
  );
}
