"use client";

import React, { useState } from "react";
import {
  Film,
  Search,
  CheckCircle,
  Clock,
  Play,
  Filter,
  RefreshCw,
  Plus,
  ShieldCheck,
  HardDrive,
  Share2,
  Check,
} from "lucide-react";
import { VideoItem } from "@/lib/api";

interface VideosTabProps {
  videos: VideoItem[];
  onRefresh: () => void;
  onPlayVideo: (video: VideoItem) => void;
  onNavigateUpload: () => void;
}

export function VideosTab({
  videos,
  onRefresh,
  onPlayVideo,
  onNavigateUpload,
}: VideosTabProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyLink = (vidId: string) => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const url = `${origin}/watch/${vidId}`;
    navigator.clipboard.writeText(url);
    setCopiedId(vidId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const filteredVideos = videos.filter((vid) => {
    const matchesSearch =
      vid.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      vid.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter =
      statusFilter === "ALL" || vid.status.toUpperCase() === statusFilter.toUpperCase();
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Film className="w-5 h-5 text-indigo-400" />
            Protected Video Library
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Browse, inspect, and stream your AES-128 encrypted HLS video catalog.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-2 rounded-xl transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={onNavigateUpload}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/25"
          >
            <Plus className="w-4 h-4" />
            Upload Video
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 p-3.5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-3 shadow-lg">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title or video ID..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          {["ALL", "READY", "PROCESSING", "QUEUED", "FAILED"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === status
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800/80"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Video Cards Grid / Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {filteredVideos.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <Film className="w-10 h-10 mx-auto text-slate-600" />
            <div className="text-sm font-semibold text-slate-300">No videos found</div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchTerm || statusFilter !== "ALL"
                ? "Try adjusting your search query or status filter."
                : "Your video library is empty. Upload your first video to get started!"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredVideos.map((vid) => (
              <div
                key={vid.id}
                className="p-4 sm:p-5 hover:bg-slate-800/30 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <h3 className="font-semibold text-sm text-slate-100 truncate">
                      {vid.title}
                    </h3>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md border bg-slate-950 border-slate-800 text-slate-400 shrink-0">
                      {vid.visibility}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span className="font-mono text-[11px] text-slate-500">
                      ID: {vid.id.slice(0, 8)}...
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3 text-indigo-400" />
                      {formatBytes(vid.raw_size_bytes)}
                    </span>
                    <span>•</span>
                    <span>{new Date(vid.created_at).toLocaleDateString()}</span>
                    <span>•</span>
                    <span className="text-indigo-400 text-[11px] flex items-center gap-1 font-mono">
                      <ShieldCheck className="w-3 h-3 text-indigo-400" />
                      AES-128
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5 ${
                      vid.status === "READY"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : vid.status === "PROCESSING"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-slate-800 text-slate-300 border border-slate-700"
                    }`}
                  >
                    {vid.status === "READY" && <CheckCircle className="w-3 h-3" />}
                    {vid.status === "PROCESSING" && <Clock className="w-3 h-3 animate-spin" />}
                    {vid.status}
                  </span>

                  {vid.status === "READY" && (
                    <>
                      <button
                        onClick={() => handleCopyLink(vid.id)}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-xl transition-all border border-slate-700/80 flex items-center gap-1.5"
                        title="Copy Secure Watch Link"
                      >
                        {copiedId === vid.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Share2 className="w-3.5 h-3.5 text-slate-400" />
                            <span>Share Link</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => onPlayVideo(vid)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/20 flex items-center gap-1.5"
                      >
                        <Play className="w-3.5 h-3.5 fill-current" />
                        Watch Stream
                      </button>
                    </>
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
