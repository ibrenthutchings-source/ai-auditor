import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Auditor Council",
  description: "Multi-agent AI governance auditor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">{children}</body>
    </html>
  );
}
