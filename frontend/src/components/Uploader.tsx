"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface UploaderProps {
  onUploadSuccess: () => void;
}

export function Uploader({ onUploadSuccess }: UploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    if (!title) {
      const defaultTitle = selectedFile.name.replace(/\.[^/.]+$/, "");
      setTitle(defaultTitle);
    }
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const startUpload = async () => {
    if (!file || !title.trim()) return;

    try {
      setIsUploading(true);
      setError(null);
      setProgress(5);
      setStatusText("Requesting upload authorization...");

      // 1. Create upload intent (FastAPI checks quota & generates presigned direct URL)
      const intent = await api.createUploadIntent(title, file.name, file.size);
      setStatusText("Uploading directly to private object storage...");

      // 2. Direct binary stream to storage via XMLHttpRequest (with real-time progress)
      const xhr = new XMLHttpRequest();
      
      await new Promise<void>((resolve, reject) => {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 90);
            setProgress(Math.max(5, percent));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            let errorDetail = `status ${xhr.status}`;
            try {
              if (xhr.responseText) {
                const parsed = JSON.parse(xhr.responseText);
                errorDetail = parsed.detail || parsed.message || xhr.responseText;
              }
            } catch {
              if (xhr.responseText) errorDetail = xhr.responseText;
            }
            reject(new Error(`Storage rejected upload (${errorDetail})`));
          }
        };

        xhr.onerror = () => reject(new Error("Network error during direct storage upload"));

        const uploadUrl = api.resolveUploadUrl(intent.upload_url);
        xhr.open(intent.method || "PUT", uploadUrl);
        if (intent.headers) {
          Object.entries(intent.headers).forEach(([k, v]) => {
            xhr.setRequestHeader(k, v as string);
          });
        }
        xhr.send(file);
      });

      // 3. Complete upload
      setProgress(95);
      setStatusText("Finalizing upload & updating quotas...");
      await api.completeUpload(intent.video_id);

      setProgress(100);
      setStatusText("Upload complete! Video registered.");
      setTimeout(() => {
        setFile(null);
        setTitle("");
        setProgress(null);
        setIsUploading(false);
        onUploadSuccess();
      }, 1200);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to upload video");
      setIsUploading(false);
      setProgress(null);
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-indigo-400" />
          Direct-to-Storage Video Upload
        </h2>
        <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded-full font-medium">
          Zero Server Hop
        </span>
      </div>

      {!file ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? "border-indigo-500 bg-indigo-950/20"
              : "border-slate-700 hover:border-slate-600 bg-slate-950/50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
          />
          <UploadCloud className="w-10 h-10 mx-auto text-slate-500 mb-3" />
          <p className="text-sm font-medium text-slate-300">
            Drag & drop your video file here, or click to browse
          </p>
          <p className="text-xs text-slate-500 mt-1">
            MP4, MOV, WebM, MKV (Processed into encrypted HLS)
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="font-medium text-slate-200 truncate">{file.name}</span>
              <span className="text-xs text-slate-400">
                {(file.size / (1024 * 1024)).toFixed(1)} MB
              </span>
            </div>

            <div className="mt-3">
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Video Title
              </label>
              <input
                type="text"
                disabled={isUploading}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a descriptive title..."
                className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {progress !== null && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">{statusText}</span>
                <span className="text-indigo-400 font-semibold">{progress}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-500 h-2 transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-950/40 border border-rose-800/50 p-3 rounded-lg">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              disabled={isUploading}
              onClick={() => { setFile(null); setError(null); }}
              className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={isUploading || !title.trim()}
              onClick={startUpload}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                "Start Upload"
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
