"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeftRight, Smartphone, AtSign, UserPlus, KeyRound, DoorClosed,
  ShieldCheck, TriangleAlert, ShieldAlert, Zap, ChevronRight, Database, Cpu, MessageSquareText, Radar,
} from "lucide-react";
import { API_URL, PageHeader, StatusPill, TIERS, decisionStyle, scoreColor, useHealth } from "./ui";

interface RiskSignal { name: string; impact: number }
interface ContextItem { type: string; relevance: string; content: string }
interface ScenarioResult {
  customer_request: string;
  action: { action_type: string; customer_id: string; amount: number | null; beneficiary_status: string | null };
  embedding_latency_ms: number;
  moss_latency_ms: number;
  risk_evaluation_latency_ms: number;
  total_guardrail_latency_ms: number;
  llm_latency_ms: number;
  decision: { risk_score: number; decision: string; explanation: string; signals: RiskSignal[]; retrieved_context: ContextItem[] };
  final_response: string;
}

const ACTIONS = [
  { id: "TRANSFER_MONEY", label: "Transfer", icon: ArrowLeftRight },
  { id: "CHANGE_PHONE", label: "Change phone", icon: Smartphone },
  { id: "CHANGE_EMAIL", label: "Change email", icon: AtSign },
  { id: "ADD_BENEFICIARY", label: "Add payee", icon: UserPlus },
  { id: "RESET_PIN", label: "Reset PIN", icon: KeyRound },
  { id: "CLOSE_ACCOUNT", label: "Close account", icon: DoorClosed },
];

const PRESETS = [
  { id: "safe", name: "Nominal traffic", desc: "Routine payment to a trusted payee", customer: "CUST_DEMO_SAFE", icon: ShieldCheck, hex: "#c6ff3d" },
  { id: "suspicious", name: "Anomalous vector", desc: "Unusual amount after a location change", customer: "CUST_DEMO_SUSP", icon: TriangleAlert, hex: "#ffb547" },
  { id: "ato", name: "Account takeover", desc: "New device, reset password, failed OTPs", customer: "CUST_DEMO_ATO", icon: ShieldAlert, hex: "#ff4d5e" },
];

const STAGES = [
  { label: "Intercept", icon: Radar },
  { label: "Retrieve", icon: Database },
  { label: "Evaluate", icon: Cpu },
  { label: "Respond", icon: MessageSquareText },
];

const CONTEXT_COLORS: Record<string, string> = {
  "Policy": "text-info border-info/30 bg-info/10",
  "Historical Case": "text-escalate border-escalate/30 bg-escalate/10",
  "Customer Timeline": "text-verify border-verify/30 bg-verify/10",
};

const pct = (value: number, max: number) => ({ "--pct": `${(value / max) * 100}%` }) as React.CSSProperties;

// ─────────────────────────────────────────────────────────────
// Semicircle gauge with the four decision tiers marked on the track
// ─────────────────────────────────────────────────────────────
function Gauge({ score }: { score: number }) {
  const cx = 110, cy = 112, r = 88;
  const point = (s: number) => {
    const a = Math.PI * (1 - s / 100);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  };
  const arc = (from: number, to: number) => {
    const [x1, y1] = point(from);
    const [x2, y2] = point(to);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  };
  const color = scoreColor(score);
  const [nx, ny] = point(score);
  return (
    <div className="relative mx-auto w-full max-w-[260px]">
      <svg viewBox="0 0 220 130" className="w-full" role="img" aria-label={`Risk score ${score} out of 100`}>
        {TIERS.map((t) => (
          <path key={t.from} d={arc(t.from + 0.6, t.to - 0.6)} stroke={t.hex} strokeOpacity={0.16} strokeWidth={12} fill="none" />
        ))}
        <motion.path
          d={arc(0, Math.max(score, 0.5))}
          stroke={color}
          strokeWidth={12}
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
          style={{ filter: `drop-shadow(0 0 10px ${color}88)` }}
        />
        <motion.circle cx={nx} cy={ny} r={7} fill="#fff" stroke={color} strokeWidth={4} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }} />
        {[30, 60, 85].map((s) => {
          const [x, y] = point(s);
          const [ox, oy] = [(x - cx) * 1.2 + cx, (y - cy) * 1.2 + cy];
          return <text key={s} x={ox} y={oy} fill="#5a6270" fontSize="8" textAnchor="middle" fontFamily="var(--font-jetbrains)">{s}</text>;
        })}
      </svg>
      <div className="absolute inset-x-0 bottom-1 text-center">
        <motion.p initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="font-mono text-5xl font-semibold tabular-nums text-white">
          {score}
        </motion.p>
        <p className="eyebrow mt-1">Risk score</p>
      </div>
    </div>
  );
}

function StageRail({ state }: { state: "idle" | "running" | "done" }) {
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="Guardrail pipeline">
      {STAGES.map(({ label, icon: Icon }, i) => {
        const lit = state === "done";
        return (
          <li key={label} className="relative">
            <motion.div
              title={label}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 transition-colors sm:justify-start ${lit ? "border-accent/30 bg-accent/[0.06]" : "border-line bg-white/[0.02]"}`}
              animate={state === "running" ? { opacity: [0.4, 1, 0.4] } : { opacity: 1 }}
              transition={state === "running" ? { duration: 1.2, repeat: Infinity, delay: i * 0.2 } : { delay: i * 0.15 }}
            >
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg ${lit ? "bg-accent text-ink" : "bg-white/5 text-muted"}`}>
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="hidden min-w-0 sm:block">
                <span className="block font-mono text-[10px] text-faint">0{i + 1}</span>
                <span className={`block truncate text-xs font-medium ${lit ? "text-white" : "text-muted"}`}>{label}</span>
              </span>
            </motion.div>
          </li>
        );
      })}
    </ol>
  );
}

function LatencyBar({ data }: { data: ScenarioResult }) {
  const parts = [
    { label: "Query embedding", sub: "Mistral API", ms: data.embedding_latency_ms, hex: "#ffb547" },
    { label: "Moss retrieval", sub: "in-process index", ms: data.moss_latency_ms, hex: "#c6ff3d" },
    { label: "Risk engine", sub: "deterministic rules", ms: data.risk_evaluation_latency_ms, hex: "#5cc8ff" },
    { label: "LLM reply", sub: "agent phrasing", ms: data.llm_latency_ms, hex: "#a98bff" },
  ];
  const total = parts.reduce((s, p) => s + p.ms, 0) || 1;
  return (
    <div className="panel p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Execution timeline</p>
          <p className="text-sm text-muted">
            Moss + risk engine decided in{" "}
            <span className="font-mono font-semibold text-accent">{(data.moss_latency_ms + data.risk_evaluation_latency_ms).toFixed(2)} ms</span>
          </p>
        </div>
        <p className="font-mono text-2xl font-semibold tabular-nums text-white">
          {(total / 1000).toFixed(2)}<span className="ml-1 text-sm text-faint">s end-to-end</span>
        </p>
      </div>
      <div className="flex h-3 w-full gap-[3px] overflow-hidden rounded-full">
        {parts.map((p, i) => (
          <motion.div
            key={p.label}
            className="h-full rounded-full"
            style={{ backgroundColor: p.hex, minWidth: 4 }}
            initial={{ flexGrow: 0 }}
            animate={{ flexGrow: p.ms / total }}
            transition={{ duration: 0.9, delay: 0.1 * i, ease: [0.22, 1, 0.36, 1] }}
          />
        ))}
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
        {parts.map((p) => (
          <div key={p.label} className="border-l border-line pl-3">
            <dt className="flex items-center gap-2 text-xs text-muted">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.hex }} /> {p.label}
            </dt>
            <dd className="mt-1 font-mono text-lg tabular-nums text-white">
              {p.ms < 10 ? p.ms.toFixed(2) : Math.round(p.ms)}<span className="ml-1 text-xs text-faint">ms</span>
            </dd>
            <dd className="text-[11px] text-faint">{p.sub}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function Home() {
  const health = useHealth();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState("");
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const [actionType, setActionType] = useState("TRANSFER_MONEY");
  const [amount, setAmount] = useState(5000);
  const [beneficiary, setBeneficiary] = useState("EXISTING");
  const [baselineRisk, setBaselineRisk] = useState(10);

  const showAmount = actionType === "TRANSFER_MONEY";
  const showBeneficiary = actionType === "TRANSFER_MONEY" || actionType === "ADD_BENEFICIARY";

  const run = async (path: string, init: RequestInit, preset: string | null) => {
    setActivePreset(preset);
    setLoading(true);
    setData(null);
    setError("");
    try {
      const res = await fetch(`${API_URL}${path}`, init);
      const result = await res.json();
      if (!res.ok) throw new Error(typeof result.detail === "string" ? result.detail : `Request failed (${res.status})`);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the RiskPulse API.");
    }
    setLoading(false);
  };

  const runCustom = () =>
    run("/api/evaluate-custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_type: actionType,
        amount: showAmount ? amount : 0,
        beneficiary_status: showBeneficiary ? beneficiary : null,
        baseline_risk: baselineRisk,
      }),
    }, null);

  const runPreset = (id: string) => run(`/api/scenarios/${id}/run`, { method: "POST" }, id);

  const d = data?.decision;
  const ds = decisionStyle(d?.decision);

  return (
    <>
      <PageHeader
        eyebrow="Guardrail Console"
        title={<>Every agent action,<br /><span className="text-accent">judged before it executes.</span></>}
        subtitle="Compose a tool call or fire a threat preset. RiskPulse retrieves context from Moss, scores it deterministically and returns a decision the voice agent can speak."
      >
        <StatusPill ok={health.ok} label="API" detail={health.ok === null ? "…" : health.ok ? "online" : "offline"} />
        <StatusPill ok={health.moss} label="Moss index" detail={health.moss ? `${health.timelines} timelines` : undefined} />
      </PageHeader>

      <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        {/* ── Left: composer + presets ── */}
        <div className="flex flex-col gap-6 xl:sticky xl:top-8 xl:self-start">
          <section className="panel p-6" aria-labelledby="composer">
            <p className="eyebrow mb-1">01 · Compose</p>
            <h2 id="composer" className="mb-5 text-lg font-semibold text-white">Payload composer</h2>

            <fieldset>
              <legend className="mb-2 text-xs text-muted">Agent tool call</legend>
              <div className="grid grid-cols-3 gap-2">
                {ACTIONS.map(({ id, label, icon: Icon }) => {
                  const on = actionType === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setActionType(id)}
                      className={`flex flex-col items-start gap-2 rounded-xl border p-3 text-left text-xs transition-all ${
                        on ? "border-accent/50 bg-accent/[0.08] text-white" : "border-line bg-white/[0.02] text-muted hover:border-white/15 hover:text-white"
                      }`}
                    >
                      <Icon className={`h-4 w-4 ${on ? "text-accent" : ""}`} />
                      {label}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <AnimatePresence initial={false}>
              {showAmount && (
                <motion.div key="amount" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                  <label htmlFor="amount" className="mt-6 flex items-baseline justify-between text-xs text-muted">
                    Amount
                    <span className="font-mono text-2xl font-semibold tabular-nums text-white">₹{amount.toLocaleString("en-IN")}</span>
                  </label>
                  <input id="amount" type="range" min={0} max={100000} step={500} value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="range mt-3" style={pct(amount, 100000)} />
                </motion.div>
              )}
              {showBeneficiary && (
                <motion.div key="ben" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                  <p className="mb-2 mt-6 text-xs text-muted">Beneficiary</p>
                  <div className="grid grid-cols-2 gap-1 rounded-xl border border-line bg-black/30 p-1" role="group" aria-label="Beneficiary">
                    {[["EXISTING", "Trusted payee"], ["NEW", "New / untrusted"]].map(([v, l]) => (
                      <button
                        key={v}
                        type="button"
                        aria-pressed={beneficiary === v}
                        onClick={() => setBeneficiary(v)}
                        className={`rounded-lg py-2 text-xs font-medium transition-colors ${beneficiary === v ? "bg-white text-ink" : "text-muted hover:text-white"}`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <label htmlFor="baseline" className="mt-6 flex items-baseline justify-between text-xs text-muted">
              Customer baseline risk
              <span className="font-mono text-2xl font-semibold tabular-nums" style={{ color: scoreColor(baselineRisk) }}>
                {baselineRisk}<span className="text-sm text-faint">/100</span>
              </span>
            </label>
            <input
              id="baseline" type="range" min={0} max={100} step={1} value={baselineRisk}
              onChange={(e) => setBaselineRisk(Number(e.target.value))}
              className="range mt-3"
              style={{ ...pct(baselineRisk, 100), "--track-fill": scoreColor(baselineRisk) } as React.CSSProperties}
            />

            <button
              type="button"
              onClick={runCustom}
              disabled={loading}
              className="group mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-3.5 text-sm font-semibold text-ink shadow-[0_10px_40px_-10px_rgb(198_255_61/0.7)] transition-all hover:brightness-110 disabled:opacity-50"
            >
              <Zap className="h-4 w-4 transition-transform group-hover:scale-110" />
              {loading && activePreset === null ? "Evaluating…" : "Inject payload"}
            </button>
          </section>

          <section className="panel p-6" aria-labelledby="presets">
            <p className="eyebrow mb-1">02 · Simulate</p>
            <h2 id="presets" className="mb-4 text-lg font-semibold text-white">Threat presets</h2>
            <div className="flex flex-col gap-2">
              {PRESETS.map(({ id, name, desc, customer, icon: Icon, hex }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => runPreset(id)}
                  disabled={loading}
                  className={`group flex items-center gap-3 rounded-xl border p-3 text-left transition-all disabled:opacity-60 ${
                    activePreset === id ? "border-white/20 bg-white/[0.05]" : "border-line bg-white/[0.015] hover:border-white/15 hover:bg-white/[0.04]"
                  }`}
                >
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ backgroundColor: `${hex}1a`, color: hex }}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-white">{name}</span>
                    <span className="block truncate text-xs text-muted">{desc}</span>
                    <span className="mt-1 block font-mono text-[10px] text-faint">{customer}</span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-white" />
                </button>
              ))}
            </div>
          </section>
        </div>

        {/* ── Right: pipeline results ── */}
        <section className="relative flex min-w-0 flex-col gap-6" aria-live="polite" aria-busy={loading}>
          <StageRail state={loading ? "running" : data ? "done" : "idle"} />

          {error && (
            <div role="alert" className="panel border-block/30 p-5 text-sm text-block">
              <p className="eyebrow mb-1 text-block">Request failed</p>
              {error}
            </div>
          )}

          {!data && !error && (
            <div className="panel relative grid min-h-[420px] place-items-center overflow-hidden p-10 text-center">
              {loading && <div className="scan" />}
              <div className="max-w-sm">
                <div className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl border border-line bg-white/[0.03]">
                  <Radar className={`h-7 w-7 ${loading ? "animate-pulse text-accent" : "text-faint"}`} />
                </div>
                <h3 className="text-lg font-semibold text-white">{loading ? "Intercepting agent call…" : "Awaiting payload"}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  {loading
                    ? "Embedding the request, retrieving context from Moss and scoring it against policy."
                    : "Inject a payload or run a preset. The intercepted call, retrieved context, risk score and agent reply will stream in here."}
                </p>
              </div>
            </div>
          )}

          {data && d && (
            <>
              {/* Decision hero */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className={`panel overflow-hidden border ${ds.border}`}
              >
                <div className="pointer-events-none absolute inset-0 opacity-60" style={{ background: `radial-gradient(40rem 12rem at 0% 0%, ${ds.hex}22, transparent 70%)` }} />
                <div className="relative grid gap-6 p-6 md:grid-cols-[minmax(0,1fr)_260px] md:items-center">
                  <div>
                    <p className="eyebrow mb-3">Decision</p>
                    <p className={`font-mono text-5xl font-bold tracking-tight sm:text-6xl ${ds.text}`}>{d.decision}</p>
                    <p className="mt-1 text-sm font-medium text-white">{ds.label}</p>
                    <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted">{d.explanation}</p>
                  </div>
                  <Gauge score={d.risk_score} />
                </div>
              </motion.div>

              <div className="grid gap-6 lg:grid-cols-2">
                {/* Intercept + respond */}
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="panel flex flex-col gap-5 p-6">
                  <div>
                    <p className="eyebrow mb-3">01 · Intercepted request</p>
                    <div className="rounded-2xl rounded-tl-md border border-line bg-white/[0.03] px-4 py-3 text-sm text-slate-200">
                      &ldquo;{data.customer_request}&rdquo;
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line font-mono text-xs">
                    {[
                      ["tool", data.action.action_type.toLowerCase()],
                      ["customer", data.action.customer_id],
                      ["amount", data.action.amount != null ? `₹${data.action.amount.toLocaleString("en-IN")}` : "—"],
                      ["payee", data.action.beneficiary_status ?? "—"],
                    ].map(([k, v]) => (
                      <div key={k} className="bg-surface px-3 py-2.5">
                        <dt className="text-[10px] uppercase tracking-wider text-faint">{k}</dt>
                        <dd className="mt-0.5 truncate text-slate-200">{v}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="mt-auto">
                    <p className="eyebrow mb-3">04 · Agent reply</p>
                    <div className="ml-auto max-w-[95%] rounded-2xl rounded-tr-md bg-white px-4 py-3 text-sm leading-relaxed text-ink">
                      {data.final_response}
                    </div>
                  </div>
                </motion.div>

                {/* Signals */}
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="panel p-6">
                  <p className="eyebrow mb-1">03 · Risk signals</p>
                  <p className="mb-5 text-sm text-muted">
                    Each rule adds to the customer&apos;s baseline. Tiers: allow &lt;30 · verify &lt;60 · escalate &lt;85 · block.
                  </p>
                  {d.signals.length === 0 ? (
                    <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">No risk signals fired. Clean request.</p>
                  ) : (
                    <ul className="flex flex-col gap-3">
                      {d.signals.map((s, i) => (
                        <motion.li key={s.name} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + i * 0.06 }}>
                          <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                            <span className="text-slate-200">{s.name}</span>
                            <span className="font-mono text-xs text-block">+{s.impact}</span>
                          </div>
                          <div className="h-1 overflow-hidden rounded-full bg-white/5">
                            <motion.div className="h-full rounded-full bg-block" initial={{ width: 0 }} animate={{ width: `${Math.min(s.impact / 30, 1) * 100}%` }} transition={{ delay: 0.3 + i * 0.06, duration: 0.6 }} />
                          </div>
                        </motion.li>
                      ))}
                    </ul>
                  )}
                </motion.div>
              </div>

              {/* Moss context */}
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="panel p-6">
                <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="eyebrow mb-1">02 · Moss context</p>
                    <p className="text-sm text-muted">{d.retrieved_context.length} documents retrieved · other customers&apos; timelines filtered out</p>
                  </div>
                  <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 font-mono text-xs text-accent">
                    ⚡ {data.moss_latency_ms.toFixed(2)} ms
                  </span>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {d.retrieved_context.map((ctx, i) => (
                    <motion.article
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.35 + i * 0.05 }}
                      className="rounded-xl border border-line bg-white/[0.02] p-4 transition-colors hover:border-white/15"
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <span className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${CONTEXT_COLORS[ctx.type] ?? "border-line bg-white/5 text-muted"}`}>
                          {ctx.type}
                        </span>
                        <span className="font-mono text-[10px] text-faint">#{i + 1}</span>
                      </div>
                      <p className="line-clamp-3 text-xs leading-relaxed text-slate-300">{ctx.content.replace(/\[METADATA:.*?\]\n/, "")}</p>
                    </motion.article>
                  ))}
                </div>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                <LatencyBar data={data} />
              </motion.div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
