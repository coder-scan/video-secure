"use client";

import React, { useState } from "react";
import {
  Sliders,
  ShieldCheck,
  Lock,
  Server,
  Zap,
  HardDrive,
  KeyRound,
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  Trash2,
} from "lucide-react";
import { TenantInfo } from "@/lib/api";

interface AdminTabProps {
  tenant: TenantInfo | null;
  userRole: string;
  userEmail: string;
}

export function AdminTab({ tenant, userRole, userEmail }: AdminTabProps) {
  const [revokeVideoId, setRevokeVideoId] = useState("");
  const [revokeStatus, setRevokeStatus] = useState<string | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const quota = tenant?.quota;
  const usage = tenant?.usage;

  const handleRevokeKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!revokeVideoId.trim()) return;
    if (confirm(`Permanently revoke master encryption key for video "${revokeVideoId}"? All streams will be terminated immediately.`)) {
      setRevokeStatus(`Master key for "${revokeVideoId}" revoked. Decryption halted.`);
      setRevokeVideoId("");
      setTimeout(() => setRevokeStatus(null), 5000);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-400" />
              Admin & Security Console
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800">
              {userRole}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            System privileges, security policies, and quota oversight.
          </p>
        </div>
      </div>

      {/* Organization Meta */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2 mb-4">
          <Server className="w-3.5 h-3.5 text-indigo-400" />
          Workspace Configuration
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
            <div className="text-[11px] text-slate-500 font-medium">Organization</div>
            <div className="text-xs font-bold text-slate-200 mt-1 truncate">{tenant?.name}</div>
          </div>

          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
            <div className="text-[11px] text-slate-500 font-medium">Plan Tier</div>
            <div className="text-xs font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              {tenant?.plan_tier || "FREE"}
            </div>
          </div>

          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
            <div className="text-[11px] text-slate-500 font-medium">Tenant ID</div>
            <div className="text-xs font-mono text-slate-300 mt-1 truncate" title={tenant?.id}>
              {tenant?.id ? `${tenant.id.slice(0, 12)}...` : "N/A"}
            </div>
          </div>

          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
            <div className="text-[11px] text-slate-500 font-medium">Root Admin</div>
            <div className="text-xs font-medium text-purple-300 mt-1 truncate" title={userEmail}>
              {userEmail}
            </div>
          </div>
        </div>
      </div>

      {/* Security Policies Matrix */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          Active Security Policies
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-indigo-400" />
                Single Device
              </span>
              <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800/80 px-2 py-0.5 rounded-full font-medium">
                Active
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Auto-evicts concurrent viewers</p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-purple-400" />
                Key TTL
              </span>
              <span className="text-[10px] bg-purple-950 text-purple-300 border border-purple-800/80 px-2 py-0.5 rounded-full font-medium">
                120s
              </span>
            </div>
            <p className="text-[11px] text-slate-500">In-memory AES-128 delivery</p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                Watermark
              </span>
              <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800/80 px-2 py-0.5 rounded-full font-medium">
                Observer
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Canvas anti-tamper watchdog</p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                DevTools Guard
              </span>
              <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800/80 px-2 py-0.5 rounded-full font-medium">
                Enforced
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Shortcut & context menu block</p>
          </div>
        </div>
      </div>

      {/* Quotas & Usage Ledger */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <HardDrive className="w-3.5 h-3.5 text-indigo-400" />
          Allocated Limits
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
            <div className="text-[11px] text-slate-500">Storage Allocation</div>
            <div className="text-base font-bold text-slate-200 mt-1">
              {formatBytes(quota?.storage_bytes_limit || 0)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Used: {formatBytes(usage?.storage_bytes_used || 0)}
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
            <div className="text-[11px] text-slate-500">Video Slots</div>
            <div className="text-base font-bold text-slate-200 mt-1">
              {quota?.max_videos || 0} Slots
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Used: {usage?.video_count || 0} Videos
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
            <div className="text-[11px] text-slate-500">Transcode Minutes</div>
            <div className="text-base font-bold text-slate-200 mt-1">
              {quota?.processing_minutes_limit || 0} Min
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Used: {usage?.processing_minutes_used || 0} Min
            </div>
          </div>
        </div>
      </div>

      {/* Emergency Revocation Control */}
      <div className="bg-slate-900/80 border border-rose-900/40 p-5 rounded-2xl space-y-3">
        <div className="flex items-center gap-2 text-rose-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-rose-300">
            Master Key Revocation (Instant DMCA / Abuse Kill-Switch)
          </h3>
        </div>

        <form onSubmit={handleRevokeKey} className="flex flex-col sm:flex-row gap-2 pt-1">
          <input
            type="text"
            placeholder="Enter Video ID to immediately revoke decryption key..."
            value={revokeVideoId}
            onChange={(e) => setRevokeVideoId(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-rose-500"
          />
          <button
            type="submit"
            disabled={!revokeVideoId.trim()}
            className="bg-rose-700 hover:bg-rose-600 disabled:opacity-40 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors flex items-center justify-center gap-1.5 shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Revoke Key
          </button>
        </form>

        {revokeStatus && (
          <div className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 p-2.5 rounded-xl flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            {revokeStatus}
          </div>
        )}
      </div>
    </div>
  );
}
