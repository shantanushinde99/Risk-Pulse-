"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MotionConfig } from "framer-motion";
import { LayoutGrid, AudioLines } from "lucide-react";

const NAV = [
  { href: "/", label: "Guardrail Console", icon: LayoutGrid },
  { href: "/voice-agent", label: "Voice Agent", icon: AudioLines },
];

function Logo() {
  return (
    <div className="relative grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent text-ink shadow-[0_0_30px_-4px_rgb(198_255_61/0.6)]">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M2 12h4l2.5-6 5 12 2.5-6h6" />
      </svg>
    </div>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <MotionConfig reducedMotion="user">
      <div className="console-bg flex min-h-screen">
        <nav aria-label="Main" className="sticky top-0 flex h-screen w-[68px] shrink-0 flex-col border-r border-line bg-ink/70 px-3 py-5 backdrop-blur-xl md:w-60">
          <Link href="/" className="mb-10 flex items-center gap-3 px-1">
            <Logo />
            <div className="hidden md:block">
              <p className="text-[15px] font-semibold tracking-tight text-white">RiskPulse</p>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-faint">Agent Guardrail</p>
            </div>
          </Link>

          <p className="eyebrow mb-3 hidden px-3 md:block">Workspace</p>
          <ul className="flex flex-col gap-1">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    title={label}
                    className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                      active ? "bg-white/[0.06] text-white" : "text-muted hover:bg-white/[0.03] hover:text-white"
                    }`}
                  >
                    {active && <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-accent" />}
                    <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? "text-accent" : ""}`} />
                    <span className="hidden md:block">{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>

          <div className="mt-auto hidden rounded-xl border border-line bg-white/[0.02] p-3 md:block">
            <p className="eyebrow mb-2">Pipeline</p>
            <p className="font-mono text-[11px] leading-relaxed text-muted">
              Agent → Moss → Risk Engine → Decision
            </p>
          </div>
        </nav>

        <main className="min-w-0 flex-1">
          <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-8 lg:py-12">{children}</div>
        </main>
      </div>
    </MotionConfig>
  );
}
