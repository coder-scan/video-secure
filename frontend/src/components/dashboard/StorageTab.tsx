"use client";

import React from "react";
import { Cloud } from "lucide-react";
import { StorageSettings } from "@/components/StorageSettings";

interface StorageTabProps {
  onStorageUpdated: () => void;
}

export function StorageTab({ onStorageUpdated }: StorageTabProps) {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Cloud className="w-5 h-5 text-indigo-400" />
          Cloud Storage & BYOS
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Choose where your encrypted videos are hosted. Connect your personal Google Drive account to expand free storage.
        </p>
      </div>

      <StorageSettings onStorageUpdated={onStorageUpdated} />
    </div>
  );
}
