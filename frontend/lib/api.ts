import { Camera, Zone, EventItem, AlertItem, DashboardStats } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/api/dashboard/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchCameras(): Promise<Camera[]> {
  const res = await fetch(`${API_BASE}/api/cameras`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch cameras");
  return res.json();
}

export async function createCamera(payload: Partial<Camera>): Promise<Camera> {
  const res = await fetch(`${API_BASE}/api/cameras`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create camera");
  return res.json();
}

export async function fetchAlerts(): Promise<AlertItem[]> {
  const res = await fetch(`${API_BASE}/api/alerts?limit=50`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function acknowledgeAlert(alertId: string, operatorName = "Officer"): Promise<AlertItem> {
  const res = await fetch(`${API_BASE}/api/alerts/${alertId}/acknowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operator_name: operatorName }),
  });
  if (!res.ok) throw new Error("Failed to acknowledge alert");
  return res.json();
}

export async function resolveAlert(alertId: string, operatorName = "Officer", notes = ""): Promise<AlertItem> {
  const res = await fetch(`${API_BASE}/api/alerts/${alertId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operator_name: operatorName, notes }),
  });
  if (!res.ok) throw new Error("Failed to resolve alert");
  return res.json();
}

export async function fetchEvents(): Promise<EventItem[]> {
  const res = await fetch(`${API_BASE}/api/events?limit=50`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function fetchZones(cameraId?: string): Promise<Zone[]> {
  const url = cameraId ? `${API_BASE}/api/zones?camera_id=${cameraId}` : `${API_BASE}/api/zones`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch zones");
  return res.json();
}
