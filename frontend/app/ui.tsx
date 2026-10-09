"use client";

import { useEffect, useState } from "react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL;

// One source of truth for decision styling across both pages
export const DECISION: Record<string, { text: string; bg: string; border: string; hex: string; label: string }> = {
  ALLOW: { text: "text-allow", bg: "bg-allow/10", border: "border-allow/30", hex: "#c6ff3d", label: "Allowed" },
  VERIFY: { text: "text-verify", bg: "bg-verify/10", border: "border-verify/30", hex: "#ffb547", label: "Step-up required" },
  ESCALATE: { text: "text-escalate", bg: "bg-escalate/10", border: "border-escalate/30", hex: "#a98bff", label: "Escalated to human" },
  BLOCK: { text: "text-block", bg: "bg-block/10", border: "border-block/30", hex: "#ff4d5e", label: "Blocked" },
};
const NEUTRAL = { text: "text-muted", bg: "bg-white/5", border: "border-line", hex: "#8a93a3", label: "Pending" };
export const decisionStyle = (d?: string) => (d && DECISION[d]) || NEUTRAL;

// Risk tiers, mirrored from backend risk_engine.py
export const TIERS = [
  { from: 0, to: 30, hex: "#c6ff3d" },
  { from: 30, to: 60, hex: "#ffb547" },
  { from: 60, to: 85, hex: "#a98bff" },
  { from: 85, to: 100, hex: "#ff4d5e" },
];
export const scoreColor = (s: number) => TIERS.find((t) => s < t.to)?.hex ?? TIERS[3].hex;

export function StatusPill({ ok, label, detail }: { ok: boolean | null; label: string; detail?: string }) {
  const dot = ok === null ? "bg-faint" : ok ? "bg-accent" : "bg-block";
  return (
    <div className="flex items-center gap-2 rounded-full border border-line bg-white/[0.03] px-3 py-1.5 text-xs">
      <span className="relative flex h-2 w-2">
        {ok && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${dot}`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${dot}`} />
      </span>
      <span className="text-slate-300">{label}</span>
      {detail && <span className="font-mono text-faint">{detail}</span>}
    </div>
  );
}

export interface Health {
  ok: boolean | null;
  moss: boolean | null;
  timelines: number;
}

// Polls the backend health endpoint so status indicators reflect reality
export function useHealth(intervalMs = 15000): Health {
  const [health, setHealth] = useState<Health>({ ok: null, moss: null, timelines: 0 });
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/health`);
        const d = await res.json();
        if (alive) setHealth({ ok: d.status === "ok", moss: !!d.moss_index_loaded, timelines: d.timelines_cached ?? 0 });
      } catch {
        if (alive) setHealth({ ok: false, moss: false, timelines: 0 });
      }
    };
    check();
    const id = setInterval(check, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs]);
  return health;
}

export function PageHeader({ eyebrow, title, subtitle, children }: {
  eyebrow: string;
  title: React.ReactNode;
  subtitle: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex flex-col gap-6 pb-8 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-2xl">
        <p className="eyebrow mb-3 flex items-center gap-2">
          <span className="h-px w-6 bg-accent" /> {eyebrow}
        </p>
        <h1 className="text-3xl font-semibold leading-[1.05] tracking-tight text-white sm:text-[2.6rem]">{title}</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted">{subtitle}</p>
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </header>
  );
}
