"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { EventItem } from "@/types";
import { fetchEvents } from "@/lib/api";
import { Activity, ShieldAlert } from "lucide-react";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";

export default function EventsPage() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const { isConnected, latestEvent } = useSafeCityWebSocket();

  useEffect(() => {
    fetchEvents().then(setEvents).catch(console.warn);
  }, []);

  useEffect(() => {
    if (latestEvent) {
      setEvents((prev) => [latestEvent, ...prev.filter((e) => e.id !== latestEvent.id)]);
    }
  }, [latestEvent]);

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6">
          <div>
            <h1 className="text-lg font-bold text-gray-100 flex items-center gap-2">
              <Activity className="w-5 h-5 text-accent" /> Audited Observable Events Log
            </h1>
            <p className="text-xs text-gray-400">
              Objective AI observations with confidence scores, calculated behavioral risk, and explanations
            </p>
          </div>

          <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-border/50 text-gray-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="p-3">Event Type</th>
                  <th className="p-3">Track ID</th>
                  <th className="p-3">Camera</th>
                  <th className="p-3">Risk Level & Score</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Explanations</th>
                  <th className="p-3">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-gray-500">
                      No events logged yet.
                    </td>
                  </tr>
                ) : (
                  events.map((e) => (
                    <tr key={e.id} className="hover:bg-surface-border/20">
                      <td className="p-3 font-semibold text-gray-200">
                        {e.event_type.replace(/_/g, " ").toUpperCase()}
                      </td>
                      <td className="p-3 font-mono text-gray-400">
                        {e.track_id !== null ? `#${e.track_id}` : "N/A"}
                      </td>
                      <td className="p-3 font-mono text-gray-400">{e.camera_id}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-rose-500/20 text-rose-400">
                          {e.risk_level} ({e.risk_score})
                        </span>
                      </td>
                      <td className="p-3 font-mono text-gray-300">
                        {(e.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="p-3 text-[11px] text-gray-400">
                        {e.reasons?.join(", ") || "Standard behavioral evaluation"}
                      </td>
                      <td className="p-3 font-mono text-gray-400">
                        {new Date(e.timestamp * 1000).toLocaleTimeString()}
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
