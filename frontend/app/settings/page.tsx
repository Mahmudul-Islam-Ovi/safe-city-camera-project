"use client";

import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";
import { Settings as SettingsIcon, ShieldCheck } from "lucide-react";

export default function SettingsPage() {
  const { isConnected } = useSafeCityWebSocket();

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6 max-w-4xl">
          <div>
            <h1 className="text-lg font-bold text-gray-100 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-accent" /> System Settings & Privacy Parameters
            </h1>
            <p className="text-xs text-gray-400">
              Configure detection thresholds, loitering limits, and privacy protection controls
            </p>
          </div>

          <div className="bg-surface border border-surface-border rounded-xl p-5 space-y-4">
            <h3 className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
              Privacy Safeguards
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-surface-border/20 rounded-lg">
                <div>
                  <div className="font-semibold text-gray-200">Face Blurring in Evidence</div>
                  <div className="text-gray-400 text-[11px]">
                    Automatically blur all face regions before persisting evidence frames to disk
                  </div>
                </div>
                <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 font-bold rounded">
                  ENABLED
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-surface-border/20 rounded-lg">
                <div>
                  <div className="font-semibold text-gray-200">Raw Video Storage</div>
                  <div className="text-gray-400 text-[11px]">
                    Privacy principle: Only store snapshots for confirmed high-risk alerts
                  </div>
                </div>
                <span className="px-2 py-1 bg-gray-500/20 text-gray-400 font-bold rounded">
                  DISABLED
                </span>
              </div>
            </div>

            <h3 className="text-xs font-semibold text-gray-200 uppercase tracking-wider pt-4">
              AI Detection Thresholds
            </h3>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-surface-border/20 rounded-lg">
                <span className="text-gray-400">Confidence Threshold</span>
                <div className="text-lg font-bold font-mono text-gray-100 mt-1">0.40</div>
              </div>
              <div className="p-3 bg-surface-border/20 rounded-lg">
                <span className="text-gray-400">Loitering Time Limit</span>
                <div className="text-lg font-bold font-mono text-gray-100 mt-1">120 seconds</div>
              </div>
              <div className="p-3 bg-surface-border/20 rounded-lg">
                <span className="text-gray-400">Crowd Alert Threshold</span>
                <div className="text-lg font-bold font-mono text-gray-100 mt-1">20 persons</div>
              </div>
              <div className="p-3 bg-surface-border/20 rounded-lg">
                <span className="text-gray-400">Primary Tracker</span>
                <div className="text-lg font-bold font-mono text-gray-100 mt-1">ByteTrack</div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
