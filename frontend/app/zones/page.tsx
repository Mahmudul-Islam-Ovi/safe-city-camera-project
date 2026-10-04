"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { Zone } from "@/types";
import { fetchZones } from "@/lib/api";
import { Layers, ShieldCheck, Plus } from "lucide-react";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";

export default function ZonesPage() {
  const [zones, setZones] = useState<Zone[]>([
    {
      id: "ZONE-DEMO-01",
      camera_id: "CAM-001",
      name: "Restricted Zone Alpha",
      polygon: [
        [430, 96],
        [912, 96],
        [912, 408],
        [430, 408],
      ],
      zone_type: "restricted",
      severity: "HIGH",
      enabled: true,
      created_at: Date.now() / 1000,
    },
  ]);
  const { isConnected } = useSafeCityWebSocket();

  useEffect(() => {
    fetchZones()
      .then((z) => {
        if (z.length > 0) setZones(z);
      })
      .catch(console.warn);
  }, []);

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                <Layers className="w-5 h-5 text-accent" /> Virtual Security Zones
              </h1>
              <p className="text-xs text-gray-400">
                Polygon-defined geofences triggering automated perimeter alerts upon entry
              </p>
            </div>
            <button className="flex items-center gap-2 px-3 py-2 bg-accent hover:bg-blue-600 text-white rounded-lg text-xs font-semibold">
              <Plus className="w-4 h-4" /> Define New Polygon Zone
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {zones.map((z) => (
              <div key={z.id} className="bg-surface border border-surface-border rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-gray-400">{z.id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 uppercase">
                    {z.severity}
                  </span>
                </div>
                <h3 className="font-semibold text-sm text-gray-200 mt-2">{z.name}</h3>
                <p className="text-xs text-gray-400 mt-1">Assigned Camera: {z.camera_id}</p>
                <div className="mt-3 p-2 bg-surface-border/30 rounded text-[11px] font-mono text-gray-400">
                  Polygon Vertices: {z.polygon.length} points
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
                  <span>Type: {z.zone_type.toUpperCase()}</span>
                  <span className="text-emerald-400 font-semibold">ENABLED</span>
                </div>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
