"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { Camera } from "@/types";
import { fetchCameras, createCamera } from "@/lib/api";
import { Video, Plus, Check, MapPin } from "lucide-react";
import { useSafeCityWebSocket } from "@/hooks/useWebSocket";

export default function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [newCam, setNewCam] = useState({
    id: `CAM-00${Date.now() % 100}`,
    name: "",
    location: "",
    source_type: "WEBCAM" as const,
    source_uri: "0",
  });
  const { isConnected } = useSafeCityWebSocket();

  useEffect(() => {
    fetchCameras()
      .then(setCameras)
      .catch((e) => console.warn(e));
  }, []);

  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await createCamera(newCam);
      setCameras((prev) => [...prev, created]);
      setShowModal(false);
    } catch (err) {
      alert("Failed to add camera");
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Topbar wsConnected={isConnected} />
        <main className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-100">Camera Feeds Management</h1>
              <p className="text-xs text-gray-400">Configure Webcams, MP4 test clips, or RTSP surveillance streams</p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-3 py-2 bg-accent hover:bg-blue-600 text-white rounded-lg text-xs font-semibold transition"
            >
              <Plus className="w-4 h-4" /> Add Camera
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cameras.map((c) => (
              <div key={c.id} className="bg-surface border border-surface-border rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-gray-400">{c.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">
                      {c.status}
                    </span>
                  </div>
                  <h3 className="font-semibold text-sm text-gray-200 mt-2">{c.name}</h3>
                  <p className="text-xs text-gray-400 flex items-center gap-1 mt-1">
                    <MapPin className="w-3.5 h-3.5 text-gray-500" /> {c.location}
                  </p>
                  <p className="text-xs font-mono text-gray-500 mt-2">Source: {c.source_type}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs">
                  <a href={`/dashboard`} className="text-accent hover:underline">
                    View Live Feed
                  </a>
                </div>
              </div>
            ))}
          </div>

          {showModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
              <form onSubmit={handleAddCamera} className="bg-surface border border-surface-border rounded-xl p-6 w-full max-w-md space-y-4">
                <h3 className="text-sm font-bold text-gray-100">Register New Camera Stream</h3>
                <div>
                  <label className="text-xs text-gray-400">Camera Name</label>
                  <input
                    required
                    value={newCam.name}
                    onChange={(e) => setNewCam({ ...newCam, name: e.target.value })}
                    placeholder="e.g. West Entrance"
                    className="w-full mt-1 bg-surface-border/40 border border-surface-border rounded p-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400">Location</label>
                  <input
                    value={newCam.location}
                    onChange={(e) => setNewCam({ ...newCam, location: e.target.value })}
                    placeholder="Building 3 Sector A"
                    className="w-full mt-1 bg-surface-border/40 border border-surface-border rounded p-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400">Source Type</label>
                  <select
                    value={newCam.source_type}
                    onChange={(e) => setNewCam({ ...newCam, source_type: e.target.value as any })}
                    className="w-full mt-1 bg-surface-border/40 border border-surface-border rounded p-2 text-xs text-white"
                  >
                    <option value="WEBCAM">Laptop Webcam</option>
                    <option value="VIDEO_FILE">MP4 Video File</option>
                    <option value="RTSP">RTSP Stream (CCTV)</option>
                  </select>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 bg-accent hover:bg-blue-600 text-white text-xs font-semibold rounded"
                  >
                    Save Camera
                  </button>
                </div>
              </form>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
