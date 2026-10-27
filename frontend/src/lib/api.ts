const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const API_BASE_URL = rawApiUrl.endsWith("/api/v1")
  ? rawApiUrl
  : `${rawApiUrl.replace(/\/+$/, "")}/api/v1`;


export interface QuotaInfo {
  storage_bytes_limit: number;
  max_videos: number;
  processing_minutes_limit: number;
  bandwidth_bytes_limit: number;
  max_concurrent_streams: number;
  max_devices_per_user: number;
}

export interface UsageInfo {
  storage_bytes_used: number;
  video_count: number;
  processing_minutes_used: number;
  bandwidth_bytes_used: number;
  period_start: string;
  period_end: string;
}

export interface TenantInfo {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  status: string;
  quota?: QuotaInfo;
  usage?: UsageInfo;
}

export interface VideoItem {
  id: string;
  tenant_id: string;
  creator_id: string;
  title: string;
  description?: string;
  status: string;
  duration_seconds: number;
  raw_size_bytes: number;
  visibility: string;
  created_at: string;
  updated_at: string;
}

export interface WatermarkData {
  viewer_id: string;
  viewer_email: string;
  viewer_ip: string;
  timestamp: string;
}

export interface PlaybackSessionInfo {
  session_id: string;
  video_id: string;
  manifest_url: string;
  playback_token: string;
  expires_in_seconds: number;
  watermark: WatermarkData;
  heartbeat_interval_seconds: number;
}

export interface HeartbeatResult {
  status: "ACTIVE" | "TERMINATED" | "EXPIRED";
  message?: string;
}

export const api = {
  getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("access_token");
    }
    return null;
  },

  setToken(token: string, role?: string, email?: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", token);
      if (role) localStorage.setItem("user_role", role);
      if (email) localStorage.setItem("user_email", email);
    }
  },

  getUserRole(): string {
    if (typeof window !== "undefined") {
      return localStorage.getItem("user_role") || "ADMIN";
    }
    return "ADMIN";
  },

  getUserEmail(): string {
    if (typeof window !== "undefined") {
      return localStorage.getItem("user_email") || "";
    }
    return "";
  },

  clearToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_role");
      localStorage.removeItem("user_email");
    }
  },

  async register(organizationName: string, email: string, password: string) {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        organization_name: organizationName,
        email,
        password,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }
    const data = await res.json();
    this.setToken(data.access_token, data.role, email);
    return data;
  },

  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    this.setToken(data.access_token, data.role, email);
    return data;
  },

  async adminLogin(email: string, password: string) {
    const res = await fetch(`${API_BASE_URL}/auth/admin-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Administrator authentication failed");
    }
    const data = await res.json();
    this.setToken(data.access_token, data.role, email);
    return data;
  },



  async getMyOrganization(): Promise<TenantInfo> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/tenants/my-organization`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to load organization");
    return res.json();
  },

  async getVideos(): Promise<VideoItem[]> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/videos`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to load videos");
    return res.json();
  },

  async getVideo(videoId: string): Promise<VideoItem> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE_URL}/videos/${videoId}`, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to load video details");
    }
    return res.json();
  },

  resolveUrl(url: string): string {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) {
      return url;
    }
    try {
      const origin = new URL(API_BASE_URL).origin;
      return `${origin}${url.startsWith("/") ? "" : "/"}${url}`;
    } catch {
      return url;
    }
  },

  resolveUploadUrl(url: string): string {
    return this.resolveUrl(url);
  },

  async createUploadIntent(title: string, filename: string, fileSize: number) {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/videos/upload-intent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title,
        filename,
        file_size_bytes: fileSize,
        content_type: "video/mp4",
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.message || err.detail || "Failed to create upload intent");
    }
    const data = await res.json();
    if (data.upload_url) {
      data.upload_url = this.resolveUploadUrl(data.upload_url);
    }
    return data;
  },

  async completeUpload(videoId: string) {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/videos/${videoId}/complete-upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error("Failed to finalize upload");
    return res.json();
  },

  async revokeVideoKey(videoId: string): Promise<VideoItem> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/videos/${videoId}/revoke-key`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to revoke video encryption key");
    }
    return res.json();
  },

  async getPlaybackToken(videoId: string): Promise<PlaybackSessionInfo> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/playback/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ video_id: videoId }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to get playback authorization");
    }
    const data: PlaybackSessionInfo = await res.json();
    data.manifest_url = this.resolveUrl(data.manifest_url);
    return data;
  },

  async sendHeartbeat(
    playbackToken: string,
    sessionId: string,
    currentTime: number
  ): Promise<HeartbeatResult> {
    const res = await fetch(`${API_BASE_URL}/playback/heartbeat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        playback_token: playbackToken,
        current_time_seconds: currentTime,
      }),
    });
    if (!res.ok) {
      return { status: "TERMINATED", message: "Heartbeat failed" };
    }
    return res.json();
  },

  async getStorageIntegrations(): Promise<StorageIntegrationItem[]> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to load storage integrations");
    return res.json();
  },

  async connectGoogleDrive(account_email?: string): Promise<StorageIntegrationItem> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage/connect-oauth`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        provider_type: "GOOGLE_DRIVE",
        account_email,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to connect Google Drive storage");
    }
    return res.json();
  },

  async connectOAuthStorage(payload?: {
    provider_type?: string;
    refresh_token?: string;
    account_email?: string;
    folder_id?: string;
  }): Promise<StorageIntegrationItem> {
    return this.connectGoogleDrive(payload?.account_email);
  },

  async disconnectStorageIntegration(integrationId: string): Promise<void> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage/${integrationId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to disconnect storage");
  },

  // --- STAGE 5: Security Risk Engine & Anti-Piracy Intelligence ---
  async getRiskOverview(): Promise<RiskOverviewInfo> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/risk-overview`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch risk overview");
    return res.json();
  },

  async getActiveSessions(): Promise<ActiveSessionItem[]> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch active streaming sessions");
    return res.json();
  },

  async revokeSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/sessions/${sessionId}/revoke`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to revoke session");
    return res.json();
  },

  async getSecurityEvents(severity?: string, eventType?: string, limit: number = 50): Promise<SecurityEventItem[]> {
    const token = this.getToken();
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (eventType) params.set("event_type", eventType);
    params.set("limit", String(limit));

    const res = await fetch(`${API_BASE_URL}/security/events?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch security events");
    return res.json();
  },

  async getIncidents(): Promise<PiracyIncidentItem[]> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/incidents`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch piracy incidents");
    return res.json();
  },

  async updateIncidentStatus(incidentId: string, status: string, notes?: string): Promise<PiracyIncidentItem> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/incidents/${incidentId}/update-status`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status, notes }),
    });
    if (!res.ok) throw new Error("Failed to update incident status");
    return res.json();
  },

  async downloadIncidentEvidence(incidentId: string, format: "json" | "csv" = "json"): Promise<Blob> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/security/incidents/${incidentId}/evidence?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to download evidence package");
    return res.blob();
  },
};

export interface StorageIntegrationItem {
  id: string;
  provider_type: "GOOGLE_DRIVE" | string;
  status: string;
  provider_account_email?: string;
  bucket_or_folder_id?: string;
  storage_quota_bytes?: number;
  is_active: boolean;
  created_at: string;
}

export interface SecurityEventItem {
  id: string;
  tenant_id: string;
  user_id?: string;
  session_id?: string;
  video_id?: string;
  event_type: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  ip_address?: string;
  details?: string;
  created_at: string;
}

export interface ActiveSessionItem {
  session_id: string;
  user_id: string;
  user_email: string;
  video_id: string;
  video_title: string;
  ip_address: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  started_at: string;
  last_heartbeat: string;
  status: string;
}

export interface RiskOverviewInfo {
  overall_risk_level: "LOW" | "MEDIUM" | "HIGH";
  average_risk_score: number;
  active_streaming_sessions: number;
  revoked_sessions_count: number;
  total_security_events: number;
  open_piracy_incidents: number;
  recent_critical_events: SecurityEventItem[];
}

export interface PiracyIncidentItem {
  id: string;
  incident_number: string;
  video_id: string;
  video_title?: string;
  status: "DETECTED" | "UNDER_REVIEW" | "CONFIRMED" | "DISMISSED" | "RESOLVED";
  similarity_score: number;
  source_url?: string;
  suspected_user_id?: string;
  suspected_session_id?: string;
  evidence_data?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}


