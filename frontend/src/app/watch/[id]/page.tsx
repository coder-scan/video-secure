"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ShieldCheck,
  Lock,
  ArrowLeft,
  Film,
  Loader2,
  AlertTriangle,
  LogIn,
} from "lucide-react";
import { api, VideoItem } from "@/lib/api";
import { SecurePlayer } from "@/components/SecurePlayer";

export default function WatchPage() {
  const params = useParams();
  const router = useRouter();
  const videoId = typeof params?.id === "string" ? params.id : "";

  const [token, setToken] = useState<string | null>(null);
  const [video, setVideo] = useState<VideoItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick Auth State if not logged in
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);

  useEffect(() => {
    const savedToken = api.getToken();
    if (savedToken) {
      setToken(savedToken);
      loadVideo(savedToken);
    } else {
      setLoading(false);
    }
  }, [videoId]);

  const loadVideo = async (authToken: string) => {
    try {
      setLoading(true);
      setError(null);
      const videoData = await api.getVideo(videoId);
      setVideo(videoData);
    } catch (err: any) {
      setError(err.message || "Failed to load protected video information");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSubmitting(true);
    try {
      const data = await api.login(email, password);
      setToken(data.access_token);
      await loadVideo(data.access_token);
    } catch (err: any) {
      setAuthError(err.message || "Authentication failed");
    } finally {
      setAuthSubmitting(false);
    }
  };

  // If unauthenticated viewer
  if (!token) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6 bg-[#080B11] text-slate-100 relative overflow-hidden">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-indigo-600/10 rounded-full blur-[128px] pointer-events-none" />

        <div className="w-full max-w-md bg-slate-900/80 border border-slate-800/90 p-8 rounded-3xl shadow-2xl backdrop-blur-xl relative z-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-white shadow-lg bg-gradient-to-tr from-indigo-600 to-indigo-500 border border-indigo-400/30 shadow-indigo-600/30">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                Protected Stream Room
              </h1>
              <p className="text-xs text-slate-400">
                Sign in to verify your authorized playback session
              </p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Viewer Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="viewer@example.com"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
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
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {authError && (
              <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/50 p-3 rounded-xl flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authSubmitting}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-xl text-xs transition-all shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {authSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Authorizing Viewer...
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  Access Protected Video
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => router.push("/")}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors inline-flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Return to Studio Home
            </button>
          </div>
        </div>
      </main>
    );
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[#080B11] text-slate-100">
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading secure video manifest...</p>
        </div>
      </main>
    );
  }

  // Error state
  if (error || !video) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6 bg-[#080B11] text-slate-100">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-8 rounded-3xl text-center space-y-4">
          <div className="w-12 h-12 bg-rose-950/60 border border-rose-800/60 rounded-2xl flex items-center justify-center text-rose-400 mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-100">Unable to Stream Video</h2>
          <p className="text-xs text-slate-400">{error || "Video not found or access denied."}</p>
          <button
            onClick={() => router.push("/")}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-4 py-2.5 rounded-xl transition-colors inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>
        </div>
      </main>
    );
  }

  // Render theater mode with SecurePlayer
  return (
    <div className="min-h-screen bg-[#080B11] text-slate-100 flex flex-col">
      {/* Top Bar */}
      <header className="h-14 px-6 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition-colors"
            title="Back to Studio"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="h-4 w-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-semibold text-slate-200 truncate max-w-sm">
              {video.title}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-2.5 py-0.5 rounded-full font-mono flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
            AES-128 Zero-Trust Stream
          </span>
        </div>
      </header>

      {/* Player Canvas */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 max-w-6xl w-full mx-auto">
        <div className="w-full aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl border border-slate-800/80 relative">
          <SecurePlayer
            videoId={video.id}
            videoTitle={video.title}
            onClose={() => router.push("/")}
          />
        </div>

        {/* Video Metadata Footer */}
        <div className="w-full mt-6 bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-100">{video.title}</h2>
            <p className="text-xs text-slate-400">
              Protected under active single-stream concurrency policy and dynamic attribution watermark.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
            <span>Video ID: {video.id}</span>
          </div>
        </div>
      </main>
    </div>
  );
}
