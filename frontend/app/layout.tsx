import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Activity } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RiskPulse",
  description: "Zero-Latency Contextual Risk and Safety Layer for AI Agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className + " bg-[#0A0A0B]"}>
        <div className="flex h-screen overflow-hidden">
          {/* Sidebar Navigation */}
          <nav className="w-16 md:w-64 bg-[#0F0F11] border-r border-white/10 flex flex-col items-center md:items-start py-6 flex-shrink-0">
            <div className="md:px-6 mb-10 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-orange-600 flex items-center justify-center shadow-lg shadow-rose-500/20 shrink-0">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <h1 className="font-bold text-lg tracking-tight text-white hidden md:block">RiskPulse</h1>
            </div>
            
            <div className="flex flex-col w-full gap-2 px-3">
              <Link href="/" className="px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors font-medium text-sm flex items-center gap-3">
                <span className="w-5 h-5 flex items-center justify-center shrink-0">⊞</span>
                <span className="hidden md:block">Dashboard</span>
              </Link>

              <Link href="/voice-agent" className="px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors font-medium text-sm flex items-center gap-3">
                <span className="w-5 h-5 flex items-center justify-center shrink-0">🎙</span>
                <span className="hidden md:block">Voice Agent</span>
              </Link>
            </div>
          </nav>
          
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
