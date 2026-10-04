import React from "react";
import { Users, AlertTriangle, ShieldCheck, Video, Flame } from "lucide-react";
import { DashboardStats } from "@/types";

interface StatsGridProps {
  stats: DashboardStats;
}

export function StatsGrid({ stats }: StatsGridProps) {
  const cards = [
    {
      title: "Active Cameras",
      value: `${stats.online_cameras} / ${stats.total_cameras}`,
      sub: "Streams monitored",
      icon: Video,
      color: "text-blue-400",
    },
    {
      title: "People Detected",
      value: stats.people_detected,
      sub: "In monitored zones",
      icon: Users,
      color: "text-emerald-400",
    },
    {
      title: "Active Alerts",
      value: stats.active_alerts,
      sub: "Requires review",
      icon: AlertTriangle,
      color: stats.active_alerts > 0 ? "text-amber-400" : "text-gray-400",
    },
    {
      title: "High Risk Events",
      value: stats.high_risk_events,
      sub: "High/Critical severity",
      icon: Flame,
      color: stats.high_risk_events > 0 ? "text-rose-400" : "text-gray-400",
    },
    {
      title: "Events Today",
      value: stats.events_today,
      sub: "Audited observations",
      icon: ShieldCheck,
      color: "text-purple-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className="bg-surface border border-surface-border rounded-xl p-4 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400">{c.title}</span>
              <Icon className={`w-4 h-4 ${c.color}`} />
            </div>
            <div className="mt-3">
              <span className="text-2xl font-bold text-gray-100 font-mono">{c.value}</span>
              <p className="text-[11px] text-gray-500 mt-0.5">{c.sub}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
