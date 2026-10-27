"use client";

import React, { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import {
  ShieldAlert,
  Lock,
  X,
  AlertTriangle,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  Loader2,
} from "lucide-react";
import { api, PlaybackSessionInfo, WatermarkData } from "@/lib/api";

interface SecurePlayerProps {
  videoId: string;
  videoTitle: string;
  onClose: () => void;
}

export function SecurePlayer({ videoId, videoTitle, onClose }: SecurePlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [session, setSession] = useState<PlaybackSessionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [concurrencyError, setConcurrencyError] = useState<string | null>(null);
  const [securityViolation, setSecurityViolation] = useState<string | null>(null);

  // Player controls
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Floating watermark position
  const [watermarkPos, setWatermarkPos] = useState({ x: 20, y: 30 });

  // 1. Initial Handshake: Request Playback Token & Ephemeral Session
  useEffect(() => {
    let isCancelled = false;

    const initPlayback = async () => {
      try {
        setLoading(true);
        setError(null);
        setConcurrencyError(null);

        const sessionInfo = await api.getPlaybackToken(videoId);
        if (isCancelled) return;

        setSession(sessionInfo);
      } catch (err: any) {
        if (!isCancelled) {
          setError(err.message || "Failed to initialize secure playback session");
          setLoading(false);
        }
      }
    };

    initPlayback();

    return () => {
      isCancelled = true;
    };
  }, [videoId]);

  // 2. Initialize Hls.js with Authenticated Header Handshake
  useEffect(() => {
    if (!session || !videoRef.current) return;

    let hls: Hls | null = null;
    const video = videoRef.current;

    if (Hls.isSupported()) {
      hls = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: true,
        xhrSetup: (xhr, url) => {
          // If loading key or manifest, attach Authorization Bearer token
          if (url.includes("/playback/")) {
            xhr.setRequestHeader("Authorization", `Bearer ${session.playback_token}`);
          }
        },
      });

      hls.loadSource(session.manifest_url);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setLoading(false);
        setError(null);
        setConcurrencyError(null);
        video.play().catch(() => {
          // Autoplay blocked by browser policy
          setIsPlaying(false);
        });
      });

      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              if (data.response && data.response.code === 403) {
                setConcurrencyError(
                  "Playback Session Revoked: Another device has started streaming on your account."
                );
              } else {
                hls?.startLoad();
              }
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls?.recoverMediaError();
              break;
            default:
              hls?.destroy();
              setError("Fatal stream error. Playback halted for security.");
              break;
          }
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native Safari HLS
      video.src = session.manifest_url;
      video.addEventListener("loadedmetadata", () => {
        setLoading(false);
        video.play().catch(() => setIsPlaying(false));
      });
    } else {
      setError("Your browser does not support encrypted HLS playback.");
      setLoading(false);
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [session]);

  // 3. Concurrency Heartbeat Ping Loop
  useEffect(() => {
    if (!session) return;

    const intervalMs = (session.heartbeat_interval_seconds || 30) * 1000;
    const timer = setInterval(async () => {
      try {
        const res = await api.sendHeartbeat(
          session.playback_token,
          session.session_id,
          videoRef.current?.currentTime || 0
        );

        if (res.status === "TERMINATED") {
          setConcurrencyError(
            res.message || "Session terminated: Concurrent streaming detected on another device."
          );
          if (videoRef.current) {
            videoRef.current.pause();
          }
        }
      } catch (e) {
        console.warn("Heartbeat error", e);
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [session]);

  // 4. Dynamic Watermark Floating Engine & Live Timestamp
  useEffect(() => {
    if (!session) return;

    // Reposition watermark randomly every 3.5 seconds
    const moveTimer = setInterval(() => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const maxX = Math.max(10, rect.width - 240);
      const maxY = Math.max(10, rect.height - 80);

      const nextX = Math.floor(Math.random() * maxX);
      const nextY = Math.floor(Math.random() * maxY);
      setWatermarkPos({ x: nextX, y: nextY });
    }, 3500);

    return () => clearInterval(moveTimer);
  }, [session]);

  // Dynamically sync canvas buffer dimensions with container
  useEffect(() => {
    const updateSize = () => {
      if (!containerRef.current || !canvasRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        if (
          canvasRef.current.width !== Math.floor(rect.width) ||
          canvasRef.current.height !== Math.floor(rect.height)
        ) {
          canvasRef.current.width = Math.floor(rect.width);
          canvasRef.current.height = Math.floor(rect.height);
        }
      }
    };

    updateSize();
    const ro = new ResizeObserver(updateSize);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Render watermark continuously with real-time live UTC clock
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !session) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;

      if (w > 0 && h > 0) {
        ctx.clearRect(0, 0, w, h);

        // Draw floating semi-transparent tamper-evident watermark
        ctx.save();
        ctx.font = "bold 13px monospace";
        ctx.fillStyle = "rgba(255, 255, 255, 0.45)";
        ctx.shadowColor = "rgba(0, 0, 0, 0.85)";
        ctx.shadowBlur = 4;

        const dateStr = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";
        const line1 = `ID: ${session.watermark.viewer_id} | ${session.watermark.viewer_ip}`;
        const line2 = `${session.watermark.viewer_email}`;
        const line3 = `${dateStr}`;

        const safeX = Math.min(watermarkPos.x, Math.max(10, w - 240));
        const safeY = Math.min(watermarkPos.y, Math.max(25, h - 50));

        ctx.fillText(line1, safeX, safeY);
        ctx.fillText(line2, safeX, safeY + 16);
        ctx.fillText(line3, safeX, safeY + 32);
        ctx.restore();
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [watermarkPos, session]);

  // 5. Tamper Watchdog: MutationObserver on Canvas Watermark
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const observer = new MutationObserver(() => {
      const style = window.getComputedStyle(canvas);
      if (
        style.display === "none" ||
        style.visibility === "hidden" ||
        parseFloat(style.opacity) < 0.1
      ) {
        setSecurityViolation("Security Violation: Video watermark modification detected.");
        if (videoRef.current) {
          videoRef.current.pause();
        }
      }
    });

    observer.observe(canvas, {
      attributes: true,
      attributeFilter: ["style", "class", "hidden"],
    });

    return () => observer.disconnect();
  }, []);

  // 6. Anti-DevTools & Anti-Capture Interceptors
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Intercept F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U, Ctrl+S
      if (
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "i" || e.key === "J" || e.key === "j" || e.key === "C" || e.key === "c")) ||
        (e.ctrlKey && (e.key === "U" || e.key === "u" || e.key === "S" || e.key === "s"))
      ) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden && videoRef.current) {
        // Automatically pause when user minimizes or switches away
        videoRef.current.pause();
        setIsPlaying(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  // Sync canvas size with video container
  useEffect(() => {
    const syncSize = () => {
      if (containerRef.current && canvasRef.current) {
        canvasRef.current.width = containerRef.current.clientWidth;
        canvasRef.current.height = containerRef.current.clientHeight;
      }
    };
    syncSize();
    window.addEventListener("resize", syncSize);
    return () => window.removeEventListener("resize", syncSize);
  }, []);

  // Video event handlers
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !videoRef.current.muted;
    setIsMuted(videoRef.current.muted);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(console.error);
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(console.error);
      setIsFullscreen(false);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration || 0);
    }
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs)) return "00:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-5xl bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
        {/* Top Header */}
        <div className="p-4 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100 truncate max-w-md">
                {videoTitle}
              </h2>
              <p className="text-xs text-indigo-400 flex items-center gap-1 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
                AES-128 Encrypted Stream • Zero-Trust Licensing Active
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 bg-slate-800/60 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video Viewport Container */}
        <div
          ref={containerRef}
          onContextMenu={(e) => e.preventDefault()}
          className="relative aspect-video bg-black flex items-center justify-center overflow-hidden select-none"
        >
          {loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 z-20 space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-slate-400 font-medium">
                Negotiating cryptographic license key...
              </p>
            </div>
          )}

          {concurrencyError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/95 z-30 p-6 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-rose-200">Concurrent Stream Blocked</h3>
              <p className="text-xs text-slate-400 max-w-sm">{concurrencyError}</p>
              <button
                onClick={onClose}
                className="mt-2 bg-slate-800 hover:bg-slate-700 text-white text-xs px-4 py-2 rounded-lg font-medium"
              >
                Close Player
              </button>
            </div>
          )}

          {securityViolation && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-rose-950/95 z-30 p-6 text-center space-y-3">
              <AlertTriangle className="w-8 h-8 text-rose-400" />
              <h3 className="text-base font-semibold text-rose-200">Security Breach</h3>
              <p className="text-xs text-rose-300">{securityViolation}</p>
            </div>
          )}

          {error && !concurrencyError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 z-20 p-6 text-center space-y-3">
              <AlertTriangle className="w-8 h-8 text-amber-400" />
              <p className="text-xs text-slate-300 max-w-sm">{error}</p>
            </div>
          )}

          {/* HTML5 Video Layer */}
          <video
            ref={videoRef}
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onClick={togglePlay}
            className="w-full h-full object-contain"
          />

          {/* Watermark Canvas Layer (Direct Frame Overlay) */}
          <canvas
            ref={canvasRef}
            className="absolute inset-0 pointer-events-none z-10"
          />
        </div>

        {/* Custom Controls Bar */}
        <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-xs text-slate-300">
          <div className="flex items-center gap-3">
            <button
              onClick={togglePlay}
              className="p-1.5 hover:text-white hover:bg-slate-800 rounded transition-colors"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>

            <button
              onClick={toggleMute}
              className="p-1.5 hover:text-white hover:bg-slate-800 rounded transition-colors"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>

            <span className="font-mono text-slate-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-slate-500 font-mono hidden sm:inline">
              Session: {session?.session_id.slice(0, 8)}...
            </span>

            <button
              onClick={toggleFullscreen}
              className="p-1.5 hover:text-white hover:bg-slate-800 rounded transition-colors"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
