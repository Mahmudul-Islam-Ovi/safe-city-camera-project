"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { AlertItem } from "@/types";
import { fetchAlerts, acknowledgeAlert, resolveAlert } from "@/lib/api";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";
import { Bell, Clock, CheckCircle } from "lucide-react";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const { isConnected, latestAlert, alertUpdates } = useSafeCityWebSocket();

  useEffect(() => {
    fetchAlerts().then(setAlerts).catch(console.warn);
  }, []);

  useEffect(() => {
    if (latestAlert) {
      setAlerts((prev) => [latestAlert, ...prev.filter((a) => a.id !== latestAlert.id)]);
    }
  }, [latestAlert]);

  useEffect(() => {
    if (alertUpdates) {
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertUpdates.id ? { ...a, status: alertUpdates.status as any } : a
        )
      );
    }
  }, [alertUpdates]);

  const handleAck = async (id: string) => {
    const updated = await acknowledgeAlert(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  const handleRes = async (id: string) => {
    const updated = await resolveAlert(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                <Bell className="w-5 h-5 text-amber-400" /> Alert Operations Center
              </h1>
              <p className="text-xs text-gray-400">All alerts requiring human-in-the-loop review</p>
            </div>
          </div>

          <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-border/50 text-gray-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="p-3">Severity</th>
                  <th className="p-3">Title & Description</th>
                  <th className="p-3">Camera</th>
                  <th className="p-3">Time</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-gray-500">
                      No active alerts recorded.
                    </td>
                  </tr>
                ) : (
                  alerts.map((a) => (
                    <tr key={a.id} className="hover:bg-surface-border/20">
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-amber-500/20 text-amber-400">
                          {a.severity}
                        </span>
                      </td>
                      <td className="p-3">
                        <div className="font-semibold text-gray-200">{a.title}</div>
                        <div className="text-gray-400 text-[11px] line-clamp-1">{a.description}</div>
                      </td>
                      <td className="p-3 font-mono text-gray-400">{a.camera_id}</td>
                      <td className="p-3 text-gray-400 font-mono">
                        {new Date(a.created_at * 1000).toLocaleTimeString()}
                      </td>
                      <td className="p-3">
                        <span className="font-mono text-[11px] text-gray-300">{a.status}</span>
                      </td>
                      <td className="p-3 text-right space-x-2">
                        {a.status === "NEW" && (
                          <button
                            onClick={() => handleAck(a.id)}
                            className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded font-medium"
                          >
                            Acknowledge
                          </button>
                        )}
                        {a.status !== "RESOLVED" && (
                          <button
                            onClick={() => handleRes(a.id)}
                            className="px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 rounded font-medium"
                          >
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}
