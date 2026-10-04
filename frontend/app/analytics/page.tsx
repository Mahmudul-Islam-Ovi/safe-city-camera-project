"use client";

import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";
import { BarChart3 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

export default function AnalyticsPage() {
  const { isConnected } = useSafeCityWebSocket();

  const eventTypeData = [
    { name: "Zone Entry", count: 24 },
    { name: "Loitering", count: 14 },
    { name: "Running", count: 18 },
    { name: "Crowd", count: 6 },
    { name: "Fall Obs.", count: 2 },
  ];

  const riskData = [
    { name: "Low", value: 45, color: "#10b981" },
    { name: "Medium", value: 30, color: "#eab308" },
    { name: "High", value: 20, color: "#f97316" },
    { name: "Critical", value: 5, color: "#ef4444" },
  ];

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6">
          <div>
            <h1 className="text-lg font-bold text-gray-100 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-accent" /> Security Analytics & Behavioral Trends
            </h1>
            <p className="text-xs text-gray-400">
              Aggregated statistics on observable events, loitering, and crowd patterns
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-surface border border-surface-border rounded-xl p-5 h-[340px] flex flex-col">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-4">
                Observable Events by Classification
              </h3>
              <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={eventTypeData}>
                    <XAxis dataKey="name" stroke="#6b7280" fontSize={11} tickLine={false} />
                    <YAxis stroke="#6b7280" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#111827",
                        borderColor: "#1f2937",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-surface border border-surface-border rounded-xl p-5 h-[340px] flex flex-col">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-4">
                Risk Severity Breakdown
              </h3>
              <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {riskData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#111827",
                        borderColor: "#1f2937",
                        borderRadius: "8px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
