"use client";

import { useState } from "react";
import { Camera } from "@/types";
import { Maximize2, Users, AlertCircle } from "lucide-react";

interface CameraFeedCardProps {
  camera: Camera;
  peopleCount?: number;
}

const AI_URL = process.env.NEXT_PUBLIC_AI_ENGINE_URL || "http://localhost:8001";

export function CameraFeedCard({ camera, peopleCount = 0 }: CameraFeedCardProps) {
  const [streamError, setStreamError] = useState(false);
  const streamUrl = `${AI_URL}/stream/${camera.id}`;

  return (
    <div className="bg-surface border border-surface-border rounded-xl overflow-hidden flex flex-col">
      <div className="h-10 px-4 bg-surface-border/40 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-semibold text-gray-200">{camera.name}</span>
          <span className="text-[10px] text-gray-400 font-mono">({camera.id})</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[11px] text-gray-300 font-mono">
            <Users className="w-3.5 h-3.5 text-accent" /> {peopleCount}
          </span>
          <button className="text-gray-400 hover:text-white" title="Maximize">
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
        {!streamError ? (
          <img
            src={streamUrl}
            alt={camera.name}
            className="w-full h-full object-contain"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <AlertCircle className="w-8 h-8 text-amber-500/70" />
            <span className="text-xs">Stream Connecting / Offline</span>
            <button
              onClick={() => setStreamError(false)}
              className="text-[11px] text-accent hover:underline mt-1"
            >
              Retry Stream
            </button>
          </div>
        )}
      </div>

      <div className="px-4 py-2 text-[11px] text-gray-400 flex items-center justify-between border-t border-surface-border/50">
        <span>Location: {camera.location}</span>
        <span className="uppercase text-[10px] text-emerald-400 font-mono">LIVE FEED</span>
      </div>
    </div>
  );
}
