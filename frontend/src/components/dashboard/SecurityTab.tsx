"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Radio,
  FileText,
  Download,
  Ban,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronRight,
  Filter,
  CheckCircle2,
  Clock,
  Eye,
  Activity,
  UserX,
  FileSpreadsheet,
} from "lucide-react";
import {
  api,
  RiskOverviewInfo,
  ActiveSessionItem,
  SecurityEventItem,
  PiracyIncidentItem,
} from "@/lib/api";

export function SecurityTab() {
  const [overview, setOverview] = useState<RiskOverviewInfo | null>(null);
  const [activeSessions, setActiveSessions] = useState<ActiveSessionItem[]>([]);
  const [events, setEvents] = useState<SecurityEventItem[]>([]);
  const [incidents, setIncidents] = useState<PiracyIncidentItem[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // New incident modal state
  const [showNewIncidentModal, setShowNewIncidentModal] = useState(false);
  const [incidentVideoId, setIncidentVideoId] = useState("");
  const [incidentSourceUrl, setIncidentSourceUrl] = useState("");
  const [incidentSimilarity, setIncidentSimilarity] = useState(85.0);
  const [incidentNotes, setIncidentNotes] = useState("");

  useEffect(() => {
    loadSecurityData();
  }, [severityFilter]);

  const loadSecurityData = async () => {
    try {
      setIsLoading(true);
      const [ovData, sessData, evData, incData] = await Promise.all([
        api.getRiskOverview(),
        api.getActiveSessions(),
        api.getSecurityEvents(severityFilter || undefined),
        api.getIncidents(),
      ]);
      setOverview(ovData);
      setActiveSessions(sessData);
      setEvents(evData);
      setIncidents(incData);
    } catch (err: any) {
      console.error("Failed to load security intelligence:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      setActionLoading(sessionId);
      await api.revokeSession(sessionId);
      setStatusMessage(`Stream session ${sessionId.slice(0, 8)}... was successfully revoked.`);
      await loadSecurityData();
    } catch (err: any) {
      alert(err.message || "Failed to revoke session");
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateIncidentStatus = async (incidentId: string, newStatus: string) => {
    try {
      setActionLoading(incidentId);
      await api.updateIncidentStatus(incidentId, newStatus);
      await loadSecurityData();
    } catch (err: any) {
      alert(err.message || "Failed to update status");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDownloadEvidence = async (incidentId: string, incidentNumber: string, format: "json" | "csv") => {
    try {
      const blob = await api.downloadIncidentEvidence(incidentId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${incidentNumber}_evidence.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err.message || "Failed to download forensic dossier");
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "HIGH":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "MEDIUM":
        return "bg-yellow-500/10 text-yellow-300 border-yellow-500/30";
      default:
        return "bg-blue-500/10 text-blue-300 border-blue-500/30";
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 70) return "text-rose-400 bg-rose-950/40 border-rose-800/40";
    if (score >= 40) return "text-amber-400 bg-amber-950/40 border-amber-800/40";
    return "text-emerald-400 bg-emerald-950/40 border-emerald-800/40";
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-indigo-400" />
            Security Risk Engine & Anti-Piracy Intelligence
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time session monitoring, automated account-sharing detection, and cryptographic leak investigation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSecurityData}
            disabled={isLoading}
            className="px-3 py-2 bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-2 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh Intelligence
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-800/60 rounded-xl text-xs text-emerald-300 flex items-center justify-between">
          <span>{statusMessage}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-emerald-400 hover:text-emerald-200 text-xs ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Intelligence Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/70 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Threat Level</span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                overview?.overall_risk_level === "HIGH"
                  ? "bg-rose-950 text-rose-300 border-rose-800/60"
                  : overview?.overall_risk_level === "MEDIUM"
                  ? "bg-amber-950 text-amber-300 border-amber-800/60"
                  : "bg-emerald-950 text-emerald-300 border-emerald-800/60"
              }`}
            >
              {overview?.overall_risk_level || "LOW"} RISK
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{overview?.average_risk_score ?? 15}</span>
            <span className="text-xs text-slate-400">/ 100 avg index</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Calculated by real-time risk engine rules</p>
        </div>

        <div className="p-5 bg-slate-900/70 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Live Active Streams</span>
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{overview?.active_streaming_sessions ?? 0}</span>
            <span className="text-xs text-slate-400">sessions</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Continuous single-device heartbeat enforcement</p>
        </div>

        <div className="p-5 bg-slate-900/70 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Revoked / Evicted Streams</span>
            <UserX className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{overview?.revoked_sessions_count ?? 0}</span>
            <span className="text-xs text-slate-400">evictions</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Concurrent breach or manual terminations</p>
        </div>

        <div className="p-5 bg-slate-900/70 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Open Piracy Incidents</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{overview?.open_piracy_incidents ?? 0}</span>
            <span className="text-xs text-slate-400">dossiers</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Leak investigations under review</p>
        </div>
      </div>

      {/* SECTION 1: Active Streaming Sessions & Real-Time Revocation */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-slate-200">Live Active Viewer Sessions</h3>
          </div>
          <span className="text-xs text-slate-400">
            {activeSessions.length} current connection{activeSessions.length === 1 ? "" : "s"}
          </span>
        </div>

        {activeSessions.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No active video sessions currently streaming. Start playback in the Video Library or Watch page to see real-time sessions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Viewer</th>
                  <th className="py-2.5 px-3">Video Title</th>
                  <th className="py-2.5 px-3">IP Address</th>
                  <th className="py-2.5 px-3">Risk Index</th>
                  <th className="py-2.5 px-3">Last Ping</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {activeSessions.map((s) => (
                  <tr key={s.session_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-3 font-medium text-slate-100">
                      <div>{s.user_email}</div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {s.session_id.slice(0, 16)}...
                      </div>
                    </td>
                    <td className="py-3 px-3 truncate max-w-xs">{s.video_title}</td>
                    <td className="py-3 px-3 font-mono text-slate-400">{s.ip_address}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${getRiskScoreColor(
                          s.risk_score
                        )}`}
                      >
                        {s.risk_score} / 100 ({s.risk_level})
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{s.last_heartbeat}</td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleRevokeSession(s.session_id)}
                        disabled={actionLoading === s.session_id}
                        className="px-2.5 py-1 bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 rounded-lg text-[11px] font-semibold transition inline-flex items-center gap-1.5"
                      >
                        <Ban className="w-3 h-3 text-rose-400" />
                        {actionLoading === s.session_id ? "Revoking..." : "Revoke Stream"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SECTION 2: Piracy Incidents & Evidence Dossiers */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <h3 className="text-sm font-bold text-slate-200">Piracy Incidents & Evidence Dossiers</h3>
          </div>
        </div>

        {incidents.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No piracy incidents reported or flagged yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Incident #</th>
                  <th className="py-2.5 px-3">Video</th>
                  <th className="py-2.5 px-3">Similarity</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3 text-right">Evidence Package</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {incidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-3 font-mono font-bold text-slate-100">
                      {inc.incident_number}
                      {inc.source_url && (
                        <div className="text-[10px] text-indigo-400 truncate max-w-xs font-sans flex items-center gap-1 mt-0.5">
                          <ExternalLink className="w-2.5 h-2.5" />
                          {inc.source_url}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3 truncate max-w-xs">{inc.video_title || "Protected Video"}</td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              inc.similarity_score > 80
                                ? "bg-rose-500"
                                : inc.similarity_score > 50
                                ? "bg-amber-500"
                                : "bg-blue-500"
                            }`}
                            style={{ width: `${Math.min(100, inc.similarity_score)}%` }}
                          />
                        </div>
                        <span className="font-semibold">{inc.similarity_score}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <select
                        value={inc.status}
                        onChange={(e) => handleUpdateIncidentStatus(inc.id, e.target.value)}
                        className="bg-slate-950 border border-slate-800 text-slate-200 text-[11px] rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value="DETECTED">DETECTED</option>
                        <option value="UNDER_REVIEW">UNDER REVIEW</option>
                        <option value="CONFIRMED">CONFIRMED</option>
                        <option value="DISMISSED">DISMISSED</option>
                        <option value="RESOLVED">RESOLVED</option>
                      </select>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{inc.created_at.slice(0, 10)}</td>
                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleDownloadEvidence(inc.id, inc.incident_number, "json")}
                          className="px-2 py-1 bg-indigo-950/60 hover:bg-indigo-900 text-indigo-300 border border-indigo-800/60 rounded text-[11px] font-medium transition inline-flex items-center gap-1"
                          title="Download Cryptographic JSON Dossier"
                        >
                          <FileText className="w-3 h-3" />
                          JSON
                        </button>
                        <button
                          onClick={() => handleDownloadEvidence(inc.id, inc.incident_number, "csv")}
                          className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-[11px] font-medium transition inline-flex items-center gap-1"
                          title="Download Evidence CSV"
                        >
                          <FileSpreadsheet className="w-3 h-3" />
                          CSV
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SECTION 3: Security Audit Log with Severity Filter */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-200">Security Audit Events</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400">Filter Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-2.5 py-1.5 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
              <option value="INFO">INFO</option>
            </select>
          </div>
        </div>

        {events.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No security audit events recorded for current filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Risk Score</th>
                  <th className="py-2.5 px-3">IP Address</th>
                  <th className="py-2.5 px-3">Details / Triggers</th>
                  <th className="py-2.5 px-3 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-3 font-mono font-medium text-slate-200">
                      {ev.event_type}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${getSeverityBadge(
                          ev.severity
                        )}`}
                      >
                        {ev.severity}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-300">{ev.risk_score}</td>
                    <td className="py-3 px-3 font-mono text-slate-400">{ev.ip_address || "—"}</td>
                    <td className="py-3 px-3 max-w-sm truncate text-slate-400 font-mono text-[11px]">
                      {ev.details || "—"}
                    </td>
                    <td className="py-3 px-3 text-right text-slate-400">{ev.created_at.slice(0, 19).replace("T", " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
