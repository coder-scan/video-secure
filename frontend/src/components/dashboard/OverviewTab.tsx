"use client";

import React from "react";
import {
  HardDrive,
  Film,
  Clock,
  Zap,
  Play,
  CheckCircle,
  Plus,
  Cloud,
} from "lucide-react";
import { TenantInfo, VideoItem } from "@/lib/api";
import { DashboardTab } from "./Sidebar";

interface OverviewTabProps {
  tenant: TenantInfo | null;
  videos: VideoItem[];
  onNavigate: (tab: DashboardTab) => void;
  onPlayVideo: (video: VideoItem) => void;
}

export function OverviewTab({
  tenant,
  videos,
  onNavigate,
  onPlayVideo,
}: OverviewTabProps) {
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const storageLimit = tenant?.quota?.storage_bytes_limit || 5 * 1024 * 1024 * 1024;
  const storageUsed = tenant?.usage?.storage_bytes_used || 0;
  const storagePercent = Math.min(100, Math.round((storageUsed / storageLimit) * 100));

  const videoLimit = tenant?.quota?.max_videos || 10;
  const videoUsed = tenant?.usage?.video_count || 0;
  const videoPercent = Math.min(100, Math.round((videoUsed / videoLimit) * 100));

  const procLimit = tenant?.quota?.processing_minutes_limit || 120;
  const procUsed = tenant?.usage?.processing_minutes_used || 0;
  const procPercent = Math.min(100, Math.round((procUsed / procLimit) * 100));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Overview of your storage quotas, active slots, and recent videos.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate("storage")}
            className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3.5 py-2 rounded-xl transition-colors"
          >
            <Cloud className="w-3.5 h-3.5 text-emerald-400" />
            Manage Storage
          </button>
          <button
            onClick={() => onNavigate("upload")}
            className="flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            Upload Video
          </button>
        </div>
      </div>

      {/* 4 Clean Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Storage */}
        <div className="bg-slate-900/80 border border-slate-800/80 p-5 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-indigo-400" />
              Storage
            </span>
            <span className="text-xs font-mono text-indigo-400">{storagePercent}%</span>
          </div>
          <div className="text-xl font-bold text-slate-100">
            {formatBytes(storageUsed)}
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full ${storagePercent > 90 ? "bg-rose-500" : "bg-indigo-500"}`}
              style={{ width: `${storagePercent}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-500">
            Capacity: {formatBytes(storageLimit)}
          </div>
        </div>

        {/* Video Slots */}
        <div className="bg-slate-900/80 border border-slate-800/80 p-5 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
              <Film className="w-4 h-4 text-emerald-400" />
              Video Slots
            </span>
            <span className="text-xs font-mono text-emerald-400">
              {Math.max(0, videoLimit - videoUsed)} left
            </span>
          </div>
          <div className="text-xl font-bold text-slate-100">
            {videoUsed} <span className="text-xs text-slate-500 font-normal">/ {videoLimit}</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-emerald-500" style={{ width: `${videoPercent}%` }} />
          </div>
          <div className="text-[11px] text-slate-500">
            Total Allowed: {videoLimit} videos
          </div>
        </div>

        {/* Processing Quota */}
        <div className="bg-slate-900/80 border border-slate-800/80 p-5 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-400" />
              Transcode Time
            </span>
            <span className="text-xs font-mono text-amber-400">{procPercent}%</span>
          </div>
          <div className="text-xl font-bold text-slate-100">
            {procUsed} <span className="text-xs text-slate-500 font-normal">min</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-amber-500" style={{ width: `${procPercent}%` }} />
          </div>
          <div className="text-[11px] text-slate-500">
            Limit: {procLimit} min / month
          </div>
        </div>

        {/* Bandwidth Cost */}
        <div className="bg-slate-900/80 border border-slate-800/80 p-5 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-purple-400" />
              Egress Cost
            </span>
            <span className="text-xs font-mono text-emerald-400 font-medium">Free</span>
          </div>
          <div className="text-xl font-bold text-slate-100">
            $0.00
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-purple-500" style={{ width: "4%" }} />
          </div>
          <div className="text-[11px] text-slate-500">
            Zero egress fees with Cloudflare & BYOS
          </div>
        </div>
      </div>

      {/* Recent Videos Section */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-800/80 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Film className="w-4 h-4 text-indigo-400" />
            Recent Videos
          </h2>
          <button
            onClick={() => onNavigate("videos")}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
          >
            View All ({videos.length}) →
          </button>
        </div>

        {videos.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <p className="text-xs text-slate-400">No videos uploaded yet.</p>
            <button
              onClick={() => onNavigate("upload")}
              className="text-xs text-indigo-400 hover:underline font-medium"
            >
              Upload your first video
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {videos.slice(0, 4).map((vid) => (
              <div
                key={vid.id}
                className="p-4 hover:bg-slate-800/30 transition-colors flex items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-200 truncate">
                    {vid.title}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {formatBytes(vid.raw_size_bytes)} • {new Date(vid.created_at).toLocaleDateString()}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      vid.status === "READY"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {vid.status}
                  </span>

                  {vid.status === "READY" && (
                    <button
                      onClick={() => onPlayVideo(vid)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1 shadow-sm"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Play
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
