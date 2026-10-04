import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#111827",
        "surface-border": "#1f2937",
        accent: "#3b82f6",
        "risk-critical": "#ef4444",
        "risk-high": "#f97316",
        "risk-medium": "#eab308",
        "risk-low": "#10b981",
      },
    },
  },
  plugins: [],
};
export default config;
