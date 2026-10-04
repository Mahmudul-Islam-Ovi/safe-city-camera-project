import Link from "next/link";
import {
  ShieldAlert,
  Video,
  Bell,
  Activity,
  Layers,
  BarChart3,
  Settings as SettingsIcon,
} from "lucide-react";

export function Sidebar() {
  const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: Video },
    { href: "/cameras", label: "Cameras", icon: Video },
    { href: "/alerts", label: "Alerts", icon: Bell },
    { href: "/events", label: "Events", icon: Activity },
    { href: "/zones", label: "Zones", icon: Layers },
    { href: "/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/settings", label: "Settings", icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-surface-border flex flex-col h-screen fixed left-0 top-0 select-none z-30">
      <div className="h-16 flex items-center px-6 border-b border-surface-border gap-3">
        <ShieldAlert className="w-7 h-7 text-accent" />
        <div>
          <h1 className="font-bold text-base text-gray-100 tracking-wider">SAFE CITY AI</h1>
          <p className="text-[10px] text-gray-400 font-mono">SOC SURVEILLANCE</p>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-surface-border/60 transition-colors"
            >
              <Icon className="w-4 h-4 text-gray-400" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-surface-border text-xs text-gray-500 font-mono">
        <p>SYSTEM v0.1.0 (MVP)</p>
        <p className="text-[10px] text-gray-600">Privacy & Decision-Support</p>
      </div>
    </aside>
  );
}
