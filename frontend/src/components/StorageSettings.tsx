"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  Trash2,
  Loader2,
  AlertCircle,
  HardDrive,
  FolderLock,
  ArrowRight,
} from "lucide-react";
import { api, StorageIntegrationItem } from "@/lib/api";

interface StorageSettingsProps {
  onStorageUpdated: () => void;
}

export function StorageSettings({ onStorageUpdated }: StorageSettingsProps) {
  const [integrations, setIntegrations] = useState<StorageIntegrationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customEmail, setCustomEmail] = useState("");
  const [showEmailInput, setShowEmailInput] = useState(false);

  const loadIntegrations = async () => {
    try {
      setLoading(true);
      const list = await api.getStorageIntegrations();
      setIntegrations(list);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleSimpleConnect = async () => {
    try {
      setConnecting(true);
      setError(null);
      const emailToUse = customEmail.trim() || api.getUserEmail() || "creator@gmail.com";
      await api.connectGoogleDrive(emailToUse);
      await loadIntegrations();
      onStorageUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to connect Google Drive");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    if (!confirm("Disconnect Google Drive storage? Videos will revert to platform storage.")) return;
    try {
      await api.disconnectStorageIntegration(id);
      await loadIntegrations();
      onStorageUpdated();
    } catch (err: any) {
      alert("Failed to disconnect: " + err.message);
    }
  };

  const activeGDrive = integrations.find(
    (i) => i.is_active && i.provider_type === "GOOGLE_DRIVE"
  );

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Google Drive Primary Card */}
      <div
        className={`p-6 rounded-2xl border transition-all ${
          activeGDrive
            ? "bg-slate-900 border-emerald-500/50 shadow-xl shadow-emerald-950/20"
            : "bg-slate-900/80 border-slate-800 shadow-lg hover:border-slate-700"
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex items-start gap-3.5">
            {/* Google Logo Icon */}
            <div className="w-12 h-12 rounded-2xl bg-white/5 border border-slate-700/60 p-2.5 flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" className="w-7 h-7">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">Google Drive</h3>
                {activeGDrive ? (
                  <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/70 border border-emerald-700/60 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <span className="text-[11px] text-slate-400 font-medium bg-slate-800 px-2 py-0.5 rounded-full">
                    15 GB Free
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {activeGDrive
                  ? `Connected to ${activeGDrive.provider_account_email || "Google Account"}`
                  : "Connect your Google account to automatically store encrypted videos in your Google Drive."}
              </p>
            </div>
          </div>

          {/* Action Button */}
          <div className="shrink-0 flex sm:self-center">
            {activeGDrive ? (
              <button
                onClick={() => handleDisconnect(activeGDrive.id)}
                className="px-3.5 py-2 text-xs font-medium text-rose-400 hover:text-rose-200 bg-rose-950/40 hover:bg-rose-950/60 border border-rose-800/40 rounded-xl transition-all flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Disconnect</span>
              </button>
            ) : (
              <button
                onClick={handleSimpleConnect}
                disabled={connecting}
                className="w-full sm:w-auto px-5 py-2.5 bg-white hover:bg-slate-100 text-slate-900 text-xs font-semibold rounded-xl shadow-lg hover:shadow-white/10 transition-all flex items-center justify-center gap-2"
              >
                {connecting ? (
                  <Loader2 className="w-4 h-4 animate-spin text-slate-900" />
                ) : (
                  <svg viewBox="0 0 24 24" className="w-4 h-4">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                )}
                <span>Connect with Google</span>
              </button>
            )}
          </div>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="mt-4 text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-3 rounded-xl flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Connected Details Bar */}
        {activeGDrive ? (
          <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
                Active Storage Capacity
              </span>
              <span className="font-mono text-emerald-400 font-semibold">15 GB Allocation</span>
            </div>

            <div className="p-3 bg-emerald-950/20 border border-emerald-800/30 rounded-xl flex items-start gap-2.5 text-xs text-slate-300">
              <FolderLock className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                <strong>Zero Setup Required:</strong> Every video you upload is automatically encrypted and saved into your personal Google Drive folder (<code className="text-emerald-300">secure_video_platform</code>).
              </span>
            </div>
          </div>
        ) : (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
            <span>Takes only 1 click to connect your Google account.</span>
            {!showEmailInput ? (
              <button
                type="button"
                onClick={() => setShowEmailInput(true)}
                className="text-indigo-400 hover:text-indigo-300 text-[11px] underline text-left sm:text-right"
              >
                Use different Google email
              </button>
            ) : (
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="email"
                  placeholder="your-email@gmail.com"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={handleSimpleConnect}
                  disabled={connecting}
                  className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-lg font-medium"
                >
                  Save
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
