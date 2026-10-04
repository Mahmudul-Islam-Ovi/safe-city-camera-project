"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ActivityChartProps {
  data?: { time: string; count: number; events: number }[];
}

export function ActivityChart({ data }: ActivityChartProps) {
  const chartData = data && data.length > 0 ? data : [
    { time: "12:00", count: 2, events: 0 },
    { time: "12:15", count: 4, events: 1 },
    { time: "12:30", count: 7, events: 2 },
    { time: "12:45", count: 5, events: 1 },
    { time: "13:00", count: 8, events: 3 },
    { time: "13:15", count: 6, events: 1 },
  ];

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-4 flex flex-col h-[280px]">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
          Surveillance Activity & Event Frequency
        </h3>
        <span className="text-[11px] text-gray-500 font-mono">Last 2 Hours</span>
      </div>

      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" stroke="#4b5563" fontSize={11} tickLine={false} />
            <YAxis stroke="#4b5563" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#111827",
                borderColor: "#1f2937",
                borderRadius: "8px",
                fontSize: "12px",
              }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorCount)"
              name="People Count"
            />
            <Area
              type="monotone"
              dataKey="events"
              stroke="#f43f5e"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorEvents)"
              name="Risk Events"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
