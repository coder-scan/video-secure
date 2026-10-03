"use client";

import React, { useState, useEffect } from "react";
import {
  HardDrive,
  Cloud,
  CheckCircle2,
  Trash2,
  Loader2,
  AlertCircle,
  Plus,
} from "lucide-react";
import { api, StorageIntegrationItem } from "@/lib/api";

interface StorageSettingsProps {
  onStorageUpdated: () => void;
}

export function StorageSettings({ onStorageUpdated }: StorageSettingsProps) {
  const [integrations, setIntegrations] = useState<StorageIntegrationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeModal, setActiveModal] = useState<"S3" | "GDRIVE" | "ONEDRIVE" | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [s3Bucket, setS3Bucket] = useState("");
  const [s3AccessKey, setS3AccessKey] = useState("");
  const [s3SecretKey, setS3SecretKey] = useState("");
  const [s3Endpoint, setS3Endpoint] = useState("");

  const [oauthEmail, setOauthEmail] = useState("");
  const [oauthToken, setOauthToken] = useState("");

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

  const handleConnectS3 = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);
      await api.connectCustomS3({
        bucket_name: s3Bucket,
        access_key_id: s3AccessKey,
        secret_access_key: s3SecretKey,
        endpoint_url: s3Endpoint || undefined,
      });
      setActiveModal(null);
      await loadIntegrations();
      onStorageUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to connect S3 bucket");
    } finally {
      setSubmitting(false);
    }
  };

  const handleConnectOAuth = async (type: "GOOGLE_DRIVE" | "ONEDRIVE") => {
    try {
      setSubmitting(true);
      setError(null);
      await api.connectOAuthStorage({
        provider_type: type,
        refresh_token: oauthToken || `1//mock_token_${Date.now()}`,
        account_email: oauthEmail || (type === "GOOGLE_DRIVE" ? "user@gmail.com" : "user@outlook.com"),
      });
      setActiveModal(null);
      await loadIntegrations();
      onStorageUpdated();
    } catch (err: any) {
      setError(err.message || "Failed to connect storage");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    if (!confirm("Revert to default 5 GB free storage?")) return;
    try {
      await api.disconnectStorageIntegration(id);
      await loadIntegrations();
      onStorageUpdated();
    } catch (err: any) {
      alert("Failed to disconnect: " + err.message);
    }
  };

  const activeBYOS = integrations.find((i) => i.is_active);

  return (
    <div className="space-y-6">
      {/* 4 Clean Storage Provider Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Platform Default */}
        <div
          className={`p-5 rounded-2xl border transition-all ${
            !activeBYOS
              ? "bg-slate-900 border-indigo-500/50 shadow-lg shadow-indigo-950/20"
              : "bg-slate-900/60 border-slate-800/80"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <HardDrive className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-100">Platform Default</h4>
                <p className="text-xs text-slate-400">Cloudflare R2 • 5 GB Free</p>
              </div>
            </div>
            {!activeBYOS ? (
              <span className="text-[11px] font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Active
              </span>
            ) : (
              <span className="text-[11px] text-slate-500 font-medium">Inactive</span>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>Bandwidth: $0.00 Egress</span>
            <span className="text-slate-500 font-mono">Built-in</span>
          </div>
        </div>

        {/* 2. Google Drive */}
        <div
          className={`p-5 rounded-2xl border transition-all ${
            activeBYOS?.provider_type === "GOOGLE_DRIVE"
              ? "bg-slate-900 border-emerald-500/50 shadow-lg shadow-emerald-950/20"
              : "bg-slate-900/60 border-slate-800/80"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-100">Google Drive</h4>
                <p className="text-xs text-emerald-400">15 GB Free Storage</p>
              </div>
            </div>

            {activeBYOS?.provider_type === "GOOGLE_DRIVE" ? (
              <button
                onClick={() => handleDisconnect(activeBYOS.id)}
                title="Disconnect"
                className="p-1.5 text-rose-400 hover:text-rose-200 bg-rose-950/40 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => {
                  setActiveModal("GDRIVE");
                  setOauthEmail("creator@gmail.com");
                  setOauthToken("1//mock_google_drive_token");
                }}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 border border-indigo-800/60 px-3 py-1.5 rounded-lg transition-colors"
              >
                Connect
              </button>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>
              {activeBYOS?.provider_type === "GOOGLE_DRIVE"
                ? activeBYOS.provider_account_email || "Connected"
                : "Connect your personal Google Drive"}
            </span>
            <span className="text-emerald-400 font-mono">+15 GB</span>
          </div>
        </div>

        {/* 3. OneDrive */}
        <div
          className={`p-5 rounded-2xl border transition-all ${
            activeBYOS?.provider_type === "ONEDRIVE"
              ? "bg-slate-900 border-blue-500/50 shadow-lg shadow-blue-950/20"
              : "bg-slate-900/60 border-slate-800/80"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-100">Microsoft OneDrive</h4>
                <p className="text-xs text-blue-400">5 GB Free Storage</p>
              </div>
            </div>

            {activeBYOS?.provider_type === "ONEDRIVE" ? (
              <button
                onClick={() => handleDisconnect(activeBYOS.id)}
                title="Disconnect"
                className="p-1.5 text-rose-400 hover:text-rose-200 bg-rose-950/40 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => {
                  setActiveModal("ONEDRIVE");
                  setOauthEmail("creator@outlook.com");
                  setOauthToken("mock_onedrive_token");
                }}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 border border-indigo-800/60 px-3 py-1.5 rounded-lg transition-colors"
              >
                Connect
              </button>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>
              {activeBYOS?.provider_type === "ONEDRIVE"
                ? activeBYOS.provider_account_email || "Connected"
                : "Connect your personal OneDrive"}
            </span>
            <span className="text-blue-400 font-mono">+5 GB</span>
          </div>
        </div>

        {/* 4. Custom AWS S3 */}
        <div
          className={`p-5 rounded-2xl border transition-all ${
            activeBYOS?.provider_type === "CUSTOM_S3"
              ? "bg-slate-900 border-purple-500/50 shadow-lg shadow-purple-950/20"
              : "bg-slate-900/60 border-slate-800/80"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <HardDrive className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-100">Custom S3 / R2 Bucket</h4>
                <p className="text-xs text-purple-400">1 TB Quota Allocation</p>
              </div>
            </div>

            {activeBYOS?.provider_type === "CUSTOM_S3" ? (
              <button
                onClick={() => handleDisconnect(activeBYOS.id)}
                title="Disconnect"
                className="p-1.5 text-rose-400 hover:text-rose-200 bg-rose-950/40 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => setActiveModal("S3")}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 border border-indigo-800/60 px-3 py-1.5 rounded-lg transition-colors"
              >
                Connect
              </button>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>
              {activeBYOS?.provider_type === "CUSTOM_S3"
                ? activeBYOS.bucket_or_folder_id || "Connected"
                : "Own bucket credentials"}
            </span>
            <span className="text-purple-400 font-mono">1 TB</span>
          </div>
        </div>
      </div>

      {/* S3 Modal */}
      {activeModal === "S3" && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="text-sm font-bold text-slate-100">Connect S3 Bucket</h4>
            <form onSubmit={handleConnectS3} className="space-y-3">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Bucket Name</label>
                <input
                  type="text"
                  required
                  placeholder="my-bucket-name"
                  value={s3Bucket}
                  onChange={(e) => setS3Bucket(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Access Key ID</label>
                <input
                  type="text"
                  required
                  placeholder="AKIA..."
                  value={s3AccessKey}
                  onChange={(e) => setS3AccessKey(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Secret Access Key</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={s3SecretKey}
                  onChange={(e) => setS3SecretKey(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Endpoint URL (Optional)</label>
                <input
                  type="text"
                  placeholder="https://..."
                  value={s3Endpoint}
                  onChange={(e) => setS3Endpoint(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {error && (
                <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-2.5 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 py-2 rounded-xl font-medium transition-colors flex items-center gap-1.5"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Connect
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* OAuth Modal */}
      {(activeModal === "GDRIVE" || activeModal === "ONEDRIVE") && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="text-sm font-bold text-slate-100">
              Connect {activeModal === "GDRIVE" ? "Google Drive" : "OneDrive"}
            </h4>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Account Email</label>
                <input
                  type="email"
                  value={oauthEmail}
                  onChange={(e) => setOauthEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">OAuth Token</label>
                <input
                  type="password"
                  value={oauthToken}
                  onChange={(e) => setOauthToken(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              {error && (
                <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-2.5 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleConnectOAuth(activeModal === "GDRIVE" ? "GOOGLE_DRIVE" : "ONEDRIVE")}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 py-2 rounded-xl font-medium transition-colors flex items-center gap-1.5"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
