export interface Camera {
  id: string;
  name: string;
  location: string;
  source_type: "WEBCAM" | "VIDEO_FILE" | "RTSP";
  source_uri: string;
  status: "ONLINE" | "OFFLINE" | "ERROR";
  is_active: boolean;
  created_at: number;
}

export interface Zone {
  id: string;
  camera_id: string;
  name: string;
  polygon: [number, number][];
  zone_type: "restricted" | "warning" | "perimeter" | "public";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  enabled: boolean;
  created_at: number;
}

export interface EventItem {
  id: string;
  camera_id: string;
  track_id: number | null;
  event_type: string;
  confidence: number;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  timestamp: number;
  evidence_frame: string | null;
  reasons: string[];
  metadata_json?: Record<string, unknown>;
}

export interface AlertItem {
  id: string;
  event_id: string;
  camera_id: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "NEW" | "ACKNOWLEDGED" | "RESOLVED";
  title: string;
  description: string;
  evidence_frame: string | null;
  created_at: number;
  acknowledged_at?: number | null;
  acknowledged_by?: string | null;
  resolved_at?: number | null;
  resolved_by?: string | null;
  operator_notes?: string | null;
}

export interface DashboardStats {
  total_cameras: number;
  online_cameras: number;
  people_detected: number;
  active_alerts: number;
  high_risk_events: number;
  crowd_count: number;
  events_today: number;
}
