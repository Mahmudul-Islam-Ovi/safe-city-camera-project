"use client";

import { AlertItem } from "@/types";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { acknowledgeAlert, resolveAlert } from "@/lib/api";

interface AlertFeedProps {
  alerts: AlertItem[];
  onAlertUpdated: (alert: AlertItem) => void;
}

export function AlertFeed({ alerts, onAlertUpdated }: AlertFeedProps) {
  const getBadgeColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-500/20 text-rose-400 border-rose-500/30";
      case "HIGH":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "MEDIUM":
        return "bg-amber-500/20 text-amber-400 border-amber-500/30";
      default:
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      const updated = await acknowledgeAlert(alertId, "Duty Officer");
      onAlertUpdated(updated);
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolve = async (alertId: string) => {
    try {
      const updated = await resolveAlert(alertId, "Duty Officer", "Event verified and cleared");
      onAlertUpdated(updated);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl flex flex-col h-[520px]">
      <div className="h-12 px-4 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-gray-200">Real-Time Alerts</h2>
        </div>
        <span className="text-[11px] font-mono text-gray-400">{alerts.length} Active</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs">
            <CheckCircle className="w-8 h-8 text-emerald-500/60 mb-2" />
            <span>No active alerts</span>
            <span className="text-[10px] text-gray-600">All surveillance sectors nominal</span>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-surface-border/30 border border-surface-border/70 rounded-lg p-3 hover:border-surface-border transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getBadgeColor(alert.severity)}`}>
                  {alert.severity}
                </span>
                <span className="text-[10px] text-gray-500 font-mono flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(alert.created_at * 1000).toLocaleTimeString()}
                </span>
              </div>

              <h3 className="text-xs font-semibold text-gray-200 mt-1.5">{alert.title}</h3>
              <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-2">{alert.description}</p>

              {alert.evidence_frame && (
                <div className="mt-2 text-[10px] text-accent flex items-center gap-1">
                  <span>📸 Evidence Frame Recorded (Blurred)</span>
                </div>
              )}

              <div className="mt-2.5 pt-2 border-t border-surface-border/40 flex items-center justify-between">
                <span className="text-[10px] text-gray-500 font-mono">STATUS: {alert.status}</span>
                <div className="flex items-center gap-1.5">
                  {alert.status === "NEW" && (
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="px-2 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[10px] font-medium rounded transition"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alert.status !== "RESOLVED" && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-medium rounded transition"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
