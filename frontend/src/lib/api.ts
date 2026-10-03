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

  async connectCustomS3(payload: {
    bucket_name: string;
    access_key_id: string;
    secret_access_key: string;
    endpoint_url?: string;
    region_name?: string;
  }): Promise<StorageIntegrationItem> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage/connect-s3`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to connect S3 bucket");
    }
    return res.json();
  },

  async connectOAuthStorage(payload: {
    provider_type: "GOOGLE_DRIVE" | "ONEDRIVE";
    refresh_token: string;
    account_email?: string;
    folder_id?: string;
  }): Promise<StorageIntegrationItem> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage/connect-oauth`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to connect cloud storage");
    }
    return res.json();
  },

  async disconnectStorageIntegration(integrationId: string): Promise<void> {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/integrations/storage/${integrationId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to disconnect storage");
  },
};

export interface StorageIntegrationItem {
  id: string;
  provider_type: "CUSTOM_S3" | "GOOGLE_DRIVE" | "ONEDRIVE";
  status: string;
  provider_account_email?: string;
  bucket_or_folder_id?: string;
  storage_quota_bytes?: number;
  is_active: boolean;
  created_at: string;
}


