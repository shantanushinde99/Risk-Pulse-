"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Phone, PhoneOff, Mic, MicOff, User, Mail, Check, X, Radar, AudioLines, Loader2 } from "lucide-react";
import Vapi from "@vapi-ai/web";
import { API_URL, PageHeader, StatusPill, decisionStyle, scoreColor, useHealth } from "../ui";

const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY || "";
const VAPI_ASSISTANT_ID = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID || "";

interface TranscriptEntry {
  role: "assistant" | "user";
  text: string;
  timestamp: Date;
}

interface VapiMessage {
  type?: string;
  role?: string;
  transcriptType?: string;
  transcript?: string;
}

const errorMessage = (err: unknown, fallback: string) => {
  const e = err as { error?: { message?: string }; message?: string } | undefined;
  return e?.error?.message || e?.message || fallback;
};

interface FieldStatus {
  state: "idle" | "ok" | "error";
  message: string;
}
const IDLE: FieldStatus = { state: "idle", message: "" };

function VerifyField({ step, icon, label, hint, type, value, placeholder, status, disabled, onChange, onSubmit }: {
  step: number;
  icon: React.ReactNode;
  label: string;
  hint: string;
  type: "text" | "email";
  value: string;
  placeholder: string;
  status: FieldStatus;
  disabled?: boolean;
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  const id = `verify-${step}`;
  const done = status.state === "ok";
  const border = done ? "border-allow/40" : status.state === "error" ? "border-block/50" : "border-line focus-within:border-accent/50";
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} className={`relative pl-9 ${disabled && !done ? "opacity-45" : ""}`}>
      <span className={`absolute left-0 top-0 grid h-6 w-6 place-items-center rounded-full font-mono text-[11px] ${done ? "bg-allow text-ink" : "border border-line bg-white/5 text-muted"}`}>
        {done ? <Check className="h-3.5 w-3.5" /> : step}
      </span>
      <label htmlFor={id} className="flex items-center gap-1.5 text-sm font-medium text-white">
        {icon} {label}
      </label>
      <p className="mb-2 text-xs text-faint">{hint}</p>
      <div className={`flex items-center gap-1 rounded-xl border bg-black/30 p-1 transition-colors ${border}`}>
        <input
          id={id}
          type={type}
          value={value}
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent px-3 py-2 font-mono text-sm text-white placeholder:text-faint focus:outline-none disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-lg bg-white px-3.5 py-2 text-xs font-semibold text-ink transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          Verify
        </button>
      </div>
      {status.message && (
        <p role="status" className={`mt-2 flex items-start gap-1.5 text-xs ${done ? "text-allow" : "text-block"}`}>
          {done ? <Check className="mt-px h-3.5 w-3.5 shrink-0" /> : <X className="mt-px h-3.5 w-3.5 shrink-0" />}
          {status.message}
        </p>
      )}
    </form>
  );
}

interface ToolCallEvent {
  toolName: string;
  args: Record<string, unknown>;
  decision?: string;
  score?: number | null;
  explanation?: string;
  embed_ms?: number;
  moss_ms?: number;
  eval_ms?: number;
  timestamp: Date;
}

// Volume-reactive orb: lime while listening, blue while the agent speaks
function Orb({ volume, speaking, state, onStart, canStart }: {
  volume: number;
  speaking: boolean;
  state: "idle" | "connecting" | "live";
  onStart: () => void;
  canStart: boolean;
}) {
  const hex = state === "live" ? (speaking ? "#5cc8ff" : "#c6ff3d") : state === "connecting" ? "#ffb547" : "#c6ff3d";
  const level = state === "live" ? Math.min(volume * 1.6, 1) : 0;
  return (
    <div className="relative mx-auto grid h-64 w-64 place-items-center">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="absolute rounded-full border"
          style={{ borderColor: `${hex}${["40", "26", "14"][i]}`, width: 150 + i * 44, height: 150 + i * 44 }}
          animate={state === "idle" ? { scale: 1, opacity: 0.6 } : { scale: 1 + level * (0.12 + i * 0.05), opacity: 1 }}
          transition={{ type: "spring", stiffness: 180, damping: 18 }}
        />
      ))}
      <motion.div
        className="absolute h-36 w-36 rounded-full blur-2xl"
        style={{ backgroundColor: hex }}
        animate={{ opacity: state === "idle" ? 0.18 : 0.25 + level * 0.4 }}
      />
      {state === "idle" ? (
        <motion.button
          type="button"
          onClick={onStart}
          disabled={!canStart}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          aria-label="Start call"
          className="relative grid h-32 w-32 place-items-center rounded-full bg-accent text-ink shadow-[0_20px_60px_-15px_rgb(198_255_61/0.8)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span className="flex flex-col items-center gap-1">
            <Phone className="h-7 w-7" />
            <span className="text-xs font-semibold">Start call</span>
          </span>
        </motion.button>
      ) : (
        <motion.div
          className="relative grid h-32 w-32 place-items-center rounded-full"
          style={{ background: `radial-gradient(circle at 35% 30%, #ffffff, ${hex} 45%, ${hex}55 100%)` }}
          animate={{ scale: 1 + level * 0.1 }}
          transition={{ type: "spring", stiffness: 260, damping: 16 }}
        >
          {state === "connecting" ? <Loader2 className="h-8 w-8 animate-spin text-ink" /> : <AudioLines className="h-8 w-8 text-ink" />}
        </motion.div>
      )}
    </div>
  );
}

const argText = (v: unknown) => (typeof v === "number" ? v.toLocaleString("en-IN") : String(v));

// ─────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────
export default function VoiceAgentPage() {
  const health = useHealth();
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [callError, setCallError] = useState("");
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [volume, setVolume] = useState(0);
  const [muted, setMuted] = useState(false);
  const [callId, setCallId] = useState("");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [callDuration, setCallDuration] = useState(0);
  const [customerIdInput, setCustomerIdInput] = useState("");
  const [idStatus, setIdStatus] = useState<FieldStatus>(IDLE);
  const [authEmail, setAuthEmail] = useState("");
  const [emailStatus, setEmailStatus] = useState<FieldStatus>(IDLE);

  const vapiRef = useRef<Vapi | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const toolCallEndRef = useRef<HTMLDivElement>(null);

  // Create the VAPI client once and wire its events
  useEffect(() => {
    if (!VAPI_PUBLIC_KEY) return;
    const vapi = new Vapi(VAPI_PUBLIC_KEY);
    vapiRef.current = vapi;

    vapi.on("call-start", () => {
      setIsConnected(true);
      setIsConnecting(false);
    });
    vapi.on("call-end", () => {
      setIsConnected(false);
      setIsConnecting(false);
      setAssistantSpeaking(false);
      setVolume(0);
    });
    vapi.on("speech-start", () => setAssistantSpeaking(true));
    vapi.on("speech-end", () => setAssistantSpeaking(false));
    vapi.on("volume-level", (v: number) => setVolume(v));
    vapi.on("message", (msg: VapiMessage) => {
      if (msg?.type === "transcript" && msg.transcriptType === "final" && msg.transcript?.trim()) {
        setTranscript((prev) => [...prev, { role: msg.role === "user" ? "user" : "assistant", text: msg.transcript!, timestamp: new Date() }]);
      }
    });
    vapi.on("error", (err: unknown) => {
      console.error("VAPI error", err);
      setCallError(errorMessage(err, "Voice call failed. Check the VAPI keys and try again."));
      setIsConnecting(false);
    });

    return () => {
      vapi.stop();
      vapi.removeAllListeners();
      vapiRef.current = null;
    };
  }, []);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  useEffect(() => {
    toolCallEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [toolCalls]);

  // Typed verification. The backend decides; the agent only gets the backend's result text
  // (never the raw typed input), so nothing typed here can steer the LLM.
  const verify = useCallback(async (path: string, body: object): Promise<{ verified: boolean; message: string }> => {
    try {
      const res = await fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ call_id: callId, ...body }),
      });
      const data = await res.json();
      return { verified: !!data.verified, message: data.message || "Verification failed." };
    } catch (e) {
      console.error("Verification request failed", e);
      return { verified: false, message: "Could not reach the server." };
    }
  }, [callId]);

  const tellAgent = useCallback((content: string) => {
    vapiRef.current?.send({ type: "add-message", message: { role: "system", content }, triggerResponseEnabled: true });
  }, []);

  const submitCustomerId = useCallback(async () => {
    const data = await verify("/api/agent/verify-id", { customer_id: customerIdInput });
    setIdStatus({ state: data.verified ? "ok" : "error", message: data.message });
    tellAgent(
      data.verified
        ? `The caller typed their Customer ID and it was verified. Say: "${data.message}" Then continue with their original request by calling its tool again with the same details.`
        : `The caller typed a Customer ID that could not be verified. Say exactly: "${data.message}"`
    );
  }, [customerIdInput, verify, tellAgent]);

  const submitEmail = useCallback(async () => {
    const data = await verify("/api/agent/verify-email", { email: authEmail });
    setEmailStatus({ state: data.verified ? "ok" : "error", message: data.message });
    tellAgent(
      data.verified
        ? "The caller's registered email was verified. Call the tool for their pending request again with the same details now."
        : `The caller's registered email did not match. Tell them: "${data.message}"`
    );
  }, [authEmail, verify, tellAgent]);

  // Poll this call's RiskPulse evaluations while it is live
  useEffect(() => {
    if (!callId) return;
    const poll = async () => {
      try {
        const res = await fetch(`${API_URL}/api/agent/latest-evaluations?call_id=${encodeURIComponent(callId)}`);
        const data = await res.json();
        const evals: ToolCallEvent[] = (data.evaluations || []).map((ev: Omit<ToolCallEvent, "timestamp"> & { timestamp: string }) => ({
          ...ev,
          timestamp: new Date(ev.timestamp),
        }));
        setToolCalls((prev) =>
          prev.length === evals.length && prev.every((p, i) => p.timestamp.getTime() === evals[i].timestamp.getTime())
            ? prev
            : evals
        );
      } catch (e) {
        console.error("Failed to fetch evaluations", e);
      }
    };
    poll();
    if (!isConnected) return; // one final fetch after hang-up, then stop
    const pollInterval = setInterval(poll, 1000);
    return () => clearInterval(pollInterval);
  }, [callId, isConnected]);

  // Call duration timer
  useEffect(() => {
    if (!isConnected) return;
    const timer = setInterval(() => setCallDuration((prev) => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [isConnected]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const startCall = useCallback(async () => {
    if (!vapiRef.current) return;
    setIsConnecting(true);
    setCallError("");
    setTranscript([]);
    setToolCalls([]);
    setCustomerIdInput("");
    setIdStatus(IDLE);
    setAuthEmail("");
    setEmailStatus(IDLE);
    setMuted(false);
    setCallDuration(0);
    try {
      const call = await vapiRef.current.start(VAPI_ASSISTANT_ID);
      if (!call?.id) throw new Error("VAPI did not return a call");
      setCallId(call.id);
    } catch (err) {
      console.error("Failed to start call:", err);
      setCallError(errorMessage(err, "Failed to start the call."));
      setIsConnecting(false);
    }
  }, []);

  const endCall = useCallback(() => {
    vapiRef.current?.stop();
  }, []);

  const toggleMute = useCallback(() => {
    if (!vapiRef.current) return;
    const next = !vapiRef.current.isMuted();
    vapiRef.current.setMuted(next);
    setMuted(next);
  }, []);

  const callState = isConnected ? "live" : isConnecting ? "connecting" : "idle";
  const keysMissing = !VAPI_PUBLIC_KEY || !VAPI_ASSISTANT_ID;
  const statusText = isConnected
    ? assistantSpeaking ? "Agent speaking" : muted ? "Microphone muted" : "Listening"
    : isConnecting ? "Connecting to agent…" : "Ready when you are";

  return (
    <>
      <PageHeader
        eyebrow="Voice Agent"
        title={<>Talk to the bank.<br /><span className="text-accent">RiskPulse listens in.</span></>}
        subtitle="A live VAPI voice agent with 12 banking tools. Every tool call is intercepted, scored and decided before anything executes."
      >
        <StatusPill ok={health.ok} label="API" detail={health.ok === null ? "…" : health.ok ? "online" : "offline"} />
        <StatusPill ok={isConnected ? true : null} label="VAPI" detail={isConnected ? formatDuration(callDuration) : "idle"} />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-[340px_minmax(0,1fr)_minmax(0,1fr)]">
        {/* ── Call + identity ── */}
        <section className="panel flex flex-col p-6 lg:col-span-2 xl:col-span-1" aria-labelledby="call-h">
          <div className="flex items-center justify-between">
            <h2 id="call-h" className="eyebrow">Call</h2>
            {isConnected && (
              <span className="flex items-center gap-1.5 rounded-full bg-block/15 px-2.5 py-1 font-mono text-[11px] text-block">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-block" /> LIVE {formatDuration(callDuration)}
              </span>
            )}
          </div>

          <Orb volume={volume} speaking={assistantSpeaking} state={callState} onStart={startCall} canStart={!keysMissing} />

          <p className="text-center text-sm font-medium text-white" aria-live="polite">{statusText}</p>

          <AnimatePresence>
            {isConnected && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-5 flex justify-center gap-2">
                <button
                  type="button"
                  onClick={toggleMute}
                  aria-pressed={muted}
                  className={`flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm transition-colors ${muted ? "border-verify/40 bg-verify/10 text-verify" : "border-line bg-white/[0.04] text-slate-200 hover:bg-white/[0.08]"}`}
                >
                  {muted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />} {muted ? "Unmute" : "Mute"}
                </button>
                <button
                  type="button"
                  onClick={endCall}
                  className="flex items-center gap-2 rounded-full bg-block px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
                >
                  <PhoneOff className="h-4 w-4" /> End call
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {keysMissing && (
            <p className="mt-4 rounded-xl border border-verify/30 bg-verify/10 p-3 text-xs text-verify">
              Set NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID in frontend/.env, then restart the dev server.
            </p>
          )}
          {callError && <p role="alert" className="mt-4 rounded-xl border border-block/30 bg-block/10 p-3 text-xs text-block">{callError}</p>}

          <div className="mt-6 border-t border-line pt-6">
            <p className="eyebrow mb-1">Identity</p>
            <p className="mb-5 text-xs text-muted">Typed details are checked by the backend, never by the AI.</p>
            <div className="flex flex-col gap-5">
              <VerifyField
                step={1}
                icon={<User className="h-3.5 w-3.5 text-muted" />}
                label="Customer ID"
                hint="When the agent asks who you are."
                type="text"
                value={customerIdInput}
                placeholder="C9876543210"
                status={idStatus}
                disabled={!isConnected || idStatus.state === "ok"}
                onChange={(v) => { setCustomerIdInput(v); setIdStatus(IDLE); }}
                onSubmit={submitCustomerId}
              />
              <VerifyField
                step={2}
                icon={<Mail className="h-3.5 w-3.5 text-muted" />}
                label="Registered email"
                hint="Only for step-up checks on risky actions."
                type="email"
                value={authEmail}
                placeholder="name@example.com"
                status={emailStatus}
                disabled={!isConnected || idStatus.state !== "ok"}
                onChange={(v) => { setAuthEmail(v); setEmailStatus(IDLE); }}
                onSubmit={submitEmail}
              />
            </div>
          </div>
        </section>

        {/* ── Transcript ── */}
        <section className="panel flex min-w-0 flex-col overflow-hidden" aria-labelledby="transcript-h">
          <div className="flex items-center justify-between border-b border-line px-6 py-4">
            <h2 id="transcript-h" className="eyebrow">Live transcript</h2>
            <span className="font-mono text-[11px] text-faint">{transcript.length} turns</span>
          </div>
          <div className="thin-scroll h-[420px] lg:h-[620px] space-y-4 overflow-y-auto p-6" aria-live="polite">
            {transcript.length === 0 ? (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-[240px]">
                  <AudioLines className="mx-auto mb-4 h-8 w-8 text-faint" />
                  <p className="text-sm text-muted">The conversation appears here as you speak.</p>
                  <p className="mt-3 font-mono text-[11px] leading-relaxed text-faint">Try: &ldquo;Check my account status&rdquo; or &ldquo;Transfer 3,000 rupees to John&rdquo;</p>
                </div>
              </div>
            ) : (
              <AnimatePresence initial={false}>
                {transcript.map((entry, i) => {
                  const user = entry.role === "user";
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25 }}
                      className={`flex flex-col ${user ? "items-end" : "items-start"}`}
                    >
                      <span className="mb-1 px-1 font-mono text-[10px] uppercase tracking-wider text-faint">
                        {user ? "You" : "Agent"} · {entry.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <div
                        className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed ${
                          user ? "rounded-2xl rounded-tr-md bg-white text-ink" : "rounded-2xl rounded-tl-md border border-line bg-white/[0.04] text-slate-200"
                        }`}
                      >
                        {entry.text}
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </section>

        {/* ── Evaluations feed ── */}
        <section className="panel flex min-w-0 flex-col overflow-hidden" aria-labelledby="evals-h">
          <div className="flex items-center justify-between border-b border-line px-6 py-4">
            <h2 id="evals-h" className="eyebrow">RiskPulse evaluations</h2>
            <span className="font-mono text-[11px] text-faint">{toolCalls.length} events</span>
          </div>
          <div className="thin-scroll h-[420px] lg:h-[620px] overflow-y-auto p-6">
            {toolCalls.length === 0 ? (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-[240px]">
                  <Radar className="mx-auto mb-4 h-8 w-8 text-faint" />
                  <p className="text-sm text-muted">Each tool call the agent makes is scored here in real time.</p>
                </div>
              </div>
            ) : (
              <ol className="relative">
                <span className="absolute bottom-2 left-[7px] top-2 w-px bg-line" aria-hidden />
                <AnimatePresence initial={false}>
                  {toolCalls.map((tc, i) => {
                    const ds = decisionStyle(tc.decision);
                    const args = Object.entries(tc.args || {}).filter(([, v]) => v !== "" && v != null);
                    return (
                      <motion.li
                        key={`${tc.timestamp.getTime()}-${i}`}
                        initial={{ opacity: 0, x: 12 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.35 }}
                        className="relative pb-5 pl-7 last:pb-0"
                      >
                        <span className="absolute left-0 top-1.5 h-[15px] w-[15px] rounded-full border-[3px] border-ink" style={{ backgroundColor: ds.hex, boxShadow: `0 0 12px ${ds.hex}88` }} />
                        <div className="rounded-xl border border-line bg-white/[0.02] p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate font-mono text-sm text-white">{tc.toolName.replace(/_/g, " ")}</p>
                              <p className="font-mono text-[10px] text-faint">{tc.timestamp.toLocaleTimeString()}</p>
                            </div>
                            <span className={`shrink-0 rounded-md border px-2 py-1 font-mono text-[11px] font-bold ${ds.text} ${ds.bg} ${ds.border}`}>
                              {tc.decision ?? "…"}
                            </span>
                          </div>

                          {tc.score != null && (
                            <div className="mt-3 flex items-center gap-3">
                              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                                <motion.div className="h-full rounded-full" style={{ backgroundColor: scoreColor(tc.score) }} initial={{ width: 0 }} animate={{ width: `${tc.score}%` }} transition={{ duration: 0.7 }} />
                              </div>
                              <span className="font-mono text-xs tabular-nums text-slate-300">{tc.score}<span className="text-faint">/100</span></span>
                            </div>
                          )}

                          {tc.explanation && <p className="mt-3 text-xs leading-relaxed text-muted">{tc.explanation}</p>}

                          {args.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-1.5">
                              {args.map(([k, v]) => (
                                <span key={k} className="rounded-md bg-white/[0.04] px-2 py-1 font-mono text-[10px] text-slate-300">
                                  <span className="text-faint">{k.replace(/_/g, " ")}:</span> {argText(v)}
                                </span>
                              ))}
                            </div>
                          )}

                          {tc.score != null && tc.moss_ms != null && tc.eval_ms != null && (
                            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-3 font-mono text-[10px] text-faint">
                              <span>embed <span className="text-slate-300">{(tc.embed_ms ?? 0).toFixed(0)}ms</span></span>
                              <span>moss <span className="text-accent">{tc.moss_ms.toFixed(1)}ms</span></span>
                              <span>engine <span className="text-slate-300">{tc.eval_ms.toFixed(1)}ms</span></span>
                            </div>
                          )}
                        </div>
                      </motion.li>
                    );
                  })}
                </AnimatePresence>
              </ol>
            )}
            <div ref={toolCallEndRef} />
          </div>
        </section>
      </div>
    </>
  );
}
