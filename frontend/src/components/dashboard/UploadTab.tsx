"use client";

import React from "react";
import { UploadCloud, HardDrive, Film } from "lucide-react";
import { TenantInfo } from "@/lib/api";
import { Uploader } from "@/components/Uploader";

interface UploadTabProps {
  tenant: TenantInfo | null;
  onUploadSuccess: () => void;
  onNavigateVideos: () => void;
}

export function UploadTab({ tenant, onUploadSuccess, onNavigateVideos }: UploadTabProps) {
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const storageLimit = tenant?.quota?.storage_bytes_limit || 5 * 1024 * 1024 * 1024;
  const storageUsed = tenant?.usage?.storage_bytes_used || 0;
  const remainingStorage = Math.max(0, storageLimit - storageUsed);

  const videoLimit = tenant?.quota?.max_videos || 10;
  const videoUsed = tenant?.usage?.video_count || 0;
  const remainingSlots = Math.max(0, videoLimit - videoUsed);

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-indigo-400" />
          Upload Video
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Directly ingest media files. Videos are automatically encrypted and formatted for secure streaming.
        </p>
      </div>

      {/* Available Slots Bar */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="bg-slate-900/80 border border-slate-800 p-3.5 rounded-xl flex items-center gap-2.5">
          <HardDrive className="w-4 h-4 text-indigo-400 shrink-0" />
          <div className="truncate">
            <span className="text-slate-400">Available: </span>
            <span className="font-semibold text-slate-100">{formatBytes(remainingStorage)}</span>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-3.5 rounded-xl flex items-center gap-2.5">
          <Film className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="truncate">
            <span className="text-slate-400">Slots: </span>
            <span className="font-semibold text-slate-100">{remainingSlots} Remaining</span>
          </div>
        </div>
      </div>

      {/* Main Direct Uploader Component */}
      <Uploader
        onUploadSuccess={() => {
          onUploadSuccess();
          onNavigateVideos();
        }}
      />
    </div>
  );
}
