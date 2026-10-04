import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Safe City AI — Security Operations Center",
  description: "AI-based video surveillance, object tracking and behavioral risk detection",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
