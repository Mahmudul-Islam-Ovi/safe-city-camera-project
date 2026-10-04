"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { StatsGrid } from "@/components/StatsGrid";
import { CameraFeedCard } from "@/components/CameraFeedCard";
import { AlertFeed } from "@/components/AlertFeed";
import { ActivityChart } from "@/components/ActivityChart";
import { fetchStats, fetchCameras, fetchAlerts } from "@/lib/api";
import { Camera, AlertItem, DashboardStats } from "@/types";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    total_cameras: 1,
    online_cameras: 1,
    people_detected: 0,
    active_alerts: 0,
    high_risk_events: 0,
    crowd_count: 0,
    events_today: 0,
  });

  const [cameras, setCameras] = useState<Camera[]>([
    {
      id: "CAM-001",
      name: "Main Surveillance Sector A",
      location: "Central Perimeter",
      source_type: "VIDEO_FILE",
      source_uri: "videos/sample/test.mp4",
      status: "ONLINE",
      is_active: true,
      created_at: Date.now() / 1000,
    },
  ]);

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const { isConnected, latestEvent, latestAlert, alertUpdates } = useSafeCityWebSocket();

  // Load initial data
  useEffect(() => {
    async function loadInitial() {
      try {
        const s = await fetchStats();
        setStats(s);
      } catch (e) {
        console.warn("Could not fetch remote stats, using fallback defaults", e);
      }

      try {
        const c = await fetchCameras();
        if (c.length > 0) setCameras(c);
      } catch (e) {
        console.warn("Using default camera feeds", e);
      }

      try {
        const a = await fetchAlerts();
        setAlerts(a);
      } catch (e) {
        console.warn("Could not fetch alerts list", e);
      }
    }

    loadInitial();
  }, []);

  // Handle incoming WebSocket alerts
  useEffect(() => {
    if (latestAlert) {
      setAlerts((prev) => [latestAlert, ...prev.filter((a) => a.id !== latestAlert.id)]);
      setStats((prev) => ({
        ...prev,
        active_alerts: prev.active_alerts + 1,
        high_risk_events:
          latestAlert.severity === "HIGH" || latestAlert.severity === "CRITICAL"
            ? prev.high_risk_events + 1
            : prev.high_risk_events,
      }));
    }
  }, [latestAlert]);

  // Handle alert status updates
  useEffect(() => {
    if (alertUpdates) {
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertUpdates.id ? { ...a, status: alertUpdates.status as any } : a
        )
      );
      if (alertUpdates.status === "RESOLVED") {
        setStats((prev) => ({
          ...prev,
          active_alerts: Math.max(0, prev.active_alerts - 1),
        }));
      }
    }
  }, [alertUpdates]);

  const handleAlertUpdated = (updated: AlertItem) => {
    setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />

      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />

        <main className="flex-1 p-6 space-y-6">
          {/* Top KPI Cards */}
          <StatsGrid stats={stats} />

          {/* Main Grid: Left Cameras, Right Alerts */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
                  Live Camera Grid ({cameras.length} Active Feeds)
                </h2>
                <span className="text-xs text-emerald-400 font-mono">● LIVE INFERENCE</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {cameras.map((cam) => (
                  <CameraFeedCard
                    key={cam.id}
                    camera={cam}
                    peopleCount={stats.people_detected}
                  />
                ))}
              </div>
            </div>

            <div className="xl:col-span-1">
              <AlertFeed alerts={alerts} onAlertUpdated={handleAlertUpdated} />
            </div>
          </div>

          {/* Bottom Chart */}
          <ActivityChart />
        </main>
      </div>
    </div>
  );
}
