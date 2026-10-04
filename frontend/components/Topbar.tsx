"use client";

import { useState, useEffect } from "react";
import { Radio, Cpu, Database, Wifi } from "lucide-react";

interface TopbarProps {
  wsConnected: boolean;
}

export function Topbar({ wsConnected }: TopbarProps) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-surface/80 backdrop-blur border-b border-surface-border flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-300">SYSTEM ACTIVE</span>
        </div>

        <div className="hidden md:flex items-center gap-4 text-xs font-mono text-gray-400">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-accent" /> AI Engine: ONLINE
          </span>
          <span className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-accent" /> DB: READY
          </span>
          <span className="flex items-center gap-1.5">
            <Wifi className={`w-3.5 h-3.5 ${wsConnected ? "text-emerald-400" : "text-rose-500"}`} />
            WS: {wsConnected ? "CONNECTED" : "DISCONNECTED"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="px-3 py-1 bg-surface-border/50 border border-surface-border rounded font-mono text-sm text-gray-200">
          {time || "00:00:00"}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-accent text-xs font-bold">
            OP
          </div>
          <span className="text-xs text-gray-300 font-medium">Duty Officer</span>
        </div>
      </div>
    </header>
  );
}
