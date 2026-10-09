"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Shield,
  ShieldAlert,
  Activity,
  Waves,
  Bot,
  User,
  Zap,
  Cpu,
  Mail,
} from "lucide-react";
import Vapi from "@vapi-ai/web";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
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

function VerifyField({ icon, label, type, value, placeholder, status, disabled, onChange, onSubmit }: {
  icon: React.ReactNode;
  label: string;
  type: "text" | "email";
  value: string;
  placeholder: string;
  status: FieldStatus;
  disabled?: boolean;
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  const border = status.state === "ok" ? "border-emerald-500/50" : status.state === "error" ? "border-rose-500/50" : "border-white/10 focus:border-cyan-500/50";
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} className="space-y-1">
      <label className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
        {icon} {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type={type}
          value={value}
          disabled={disabled}
          autoComplete="off"
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label={label}
          className={`flex-1 bg-white/5 border rounded-lg px-4 py-2 text-sm text-white focus:outline-none placeholder:text-slate-600 disabled:opacity-50 ${border}`}
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition-colors shrink-0"
        >
          Verify
        </button>
      </div>
      {status.message && (
        <p className={`text-xs ${status.state === "ok" ? "text-emerald-400" : "text-rose-400"}`}>
          {status.state === "ok" ? "✓ " : "✗ "}{status.message}
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

// ─────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────
export default function VoiceAgentPage() {
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

  const getToolColor = (toolName: string) => {
    const riskTools = [
      "transfer_money",
      "change_phone_number",
      "change_email",
      "close_account",
      "withdraw_fixed_deposit",
    ];
    const mediumTools = [
      "process_refund",
      "add_beneficiary",
      "reset_pin",
      "increase_credit_limit",
    ];
    if (riskTools.includes(toolName))
      return "border-rose-500/30 bg-rose-500/10 text-rose-400";
    if (mediumTools.includes(toolName))
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case "ALLOW": return "text-emerald-400";
      case "VERIFY": return "text-amber-400";
      case "BLOCK": return "text-rose-500";
      case "ESCALATE": return "text-purple-400";
      default: return "text-slate-400";
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-slate-200 font-sans selection:bg-rose-500/30">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#0F0F11]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-orange-600 flex items-center justify-center shadow-lg shadow-rose-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight text-white">
                RiskPulse
              </h1>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 font-medium">
                Voice Agent Interface
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {isConnected && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-emerald-400 text-xs font-medium">
                  LIVE — {formatDuration(callDuration)}
                </span>
              </motion.div>
            )}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
              <Shield className="w-4 h-4 text-rose-400" />
              <span className="text-xs font-medium text-slate-300">
                RiskPulse Active
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Call Control Section */}
        <div className="flex justify-center mb-8">
          <div className="relative">
            {/* Animated rings when connected */}
            {isConnected && (
              <>
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-emerald-500/30"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.6, 0, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  style={{
                    width: 140,
                    height: 140,
                    top: -22,
                    left: -22,
                  }}
                />
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-emerald-500/20"
                  animate={{ scale: [1, 1.8, 1], opacity: [0.4, 0, 0.4] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: 0.5,
                  }}
                  style={{
                    width: 140,
                    height: 140,
                    top: -22,
                    left: -22,
                  }}
                />
              </>
            )}

            {/* Main call button */}
            {!isConnected && !isConnecting ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={startCall}
                disabled={!VAPI_PUBLIC_KEY || !VAPI_ASSISTANT_ID}
                aria-label="Start call"
                className="disabled:opacity-40 disabled:cursor-not-allowed w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-2xl shadow-emerald-500/30 cursor-pointer transition-all hover:shadow-emerald-500/50"
              >
                <Phone className="w-10 h-10 text-white" />
              </motion.button>
            ) : isConnecting ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-24 h-24 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-2xl shadow-amber-500/30"
              >
                <Waves className="w-10 h-10 text-white" />
              </motion.div>
            ) : (
              <div className="flex items-center gap-4">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={toggleMute}
                  aria-label={muted ? "Unmute microphone" : "Mute microphone"}
                  className="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center cursor-pointer hover:bg-white/10 transition-all"
                >
                  {muted ? <MicOff className="w-6 h-6 text-rose-400" /> : <Mic className="w-6 h-6 text-slate-300" />}
                </motion.button>

                <motion.div
                  animate={{ scale: 1 + volume * 0.25 }}
                  transition={{ duration: 0.1 }}
                  className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-2xl shadow-emerald-500/30 relative"
                >
                  <Waves className="w-10 h-10 text-white relative z-10" />
                </motion.div>

                <motion.button
                  aria-label="End call"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={endCall}
                  className="w-14 h-14 rounded-full bg-rose-500/20 border border-rose-500/30 flex items-center justify-center cursor-pointer hover:bg-rose-500/30 transition-all"
                >
                  <PhoneOff className="w-6 h-6 text-rose-400" />
                </motion.button>
              </div>
            )}
          </div>
        </div>

        {(!VAPI_PUBLIC_KEY || !VAPI_ASSISTANT_ID) && (
          <p className="text-center text-amber-400 text-sm mb-8">
            Set NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID in frontend/.env, then restart the dev server.
          </p>
        )}

        {callError && <p className="text-center text-rose-400 text-sm mb-8">{callError}</p>}

        {isConnected ? (
          <div className="flex items-center justify-center gap-2 text-xs text-slate-400 uppercase tracking-widest mb-4">
            <span className={`w-2 h-2 rounded-full animate-pulse ${assistantSpeaking ? "bg-rose-400" : "bg-emerald-400"}`} />
            {assistantSpeaking ? "Agent speaking..." : muted ? "Muted" : "Listening..."}
          </div>
        ) : (
          !isConnecting && transcript.length === 0 && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-slate-500 text-sm mb-8"
            >
              Press the button above to start a live voice call with the RiskPulse
              AI Banking Agent
            </motion.p>
          )
        )}

        {/* Two-column layout: Transcript + RiskPulse Events */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          {/* Live Transcript */}
          <div className="bg-[#0F0F11] border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-rose-400" />
                <h2 className="font-semibold text-white text-sm">
                  Live Transcript
                </h2>
              </div>
              {isConnected && (
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              )}
            </div>
            <div className="h-[500px] overflow-y-auto p-5 space-y-4">
              {transcript.length === 0 ? (
                <p className="text-slate-600 text-sm text-center mt-20">
                  Conversation will appear here...
                </p>
              ) : (
                <AnimatePresence>
                  {transcript.map((entry, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                      className={`flex gap-3 ${
                        entry.role === "user" ? "justify-end" : ""
                      }`}
                    >
                      {entry.role !== "user" && (
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                            entry.role === "assistant"
                              ? "bg-gradient-to-br from-rose-500 to-orange-600"
                              : "bg-slate-700"
                          }`}
                        >
                          {entry.role === "assistant" ? (
                            <Bot className="w-4 h-4 text-white" />
                          ) : (
                            <Zap className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                          entry.role === "user"
                            ? "bg-blue-600/20 border border-blue-500/30 text-blue-100 rounded-br-md"
                            : entry.role === "assistant"
                            ? "bg-white/5 border border-white/10 text-slate-200 rounded-bl-md"
                            : "bg-slate-800/50 border border-slate-700/50 text-slate-500 italic text-xs"
                        }`}
                      >
                        {entry.text}
                      </div>
                      {entry.role === "user" && (
                        <div className="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0">
                          <User className="w-4 h-4 text-blue-400" />
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              )}
              <div ref={transcriptEndRef} />
            </div>

            {/* Secure typed verification */}
            {isConnected && (
              <div className="p-4 border-t border-white/10 bg-black/20 space-y-3">
                <VerifyField
                  icon={<User className="w-3 h-3" />}
                  label="Customer ID"
                  type="text"
                  value={customerIdInput}
                  placeholder="e.g. C9876543210"
                  status={idStatus}
                  disabled={idStatus.state === "ok"}
                  onChange={(v) => { setCustomerIdInput(v); setIdStatus(IDLE); }}
                  onSubmit={submitCustomerId}
                />
                <VerifyField
                  icon={<Mail className="w-3 h-3" />}
                  label="Registered email (only when the agent asks)"
                  type="email"
                  value={authEmail}
                  placeholder="name@example.com"
                  status={emailStatus}
                  disabled={idStatus.state !== "ok"}
                  onChange={(v) => { setAuthEmail(v); setEmailStatus(IDLE); }}
                  onSubmit={submitEmail}
                />
              </div>
            )}
          </div>

          {/* RiskPulse Events */}
          <div className="bg-[#0F0F11] border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <h2 className="font-semibold text-white text-sm">
                  RiskPulse Evaluations
                </h2>
              </div>
              <span className="text-xs text-slate-500">
                {toolCalls.length} event{toolCalls.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="h-[500px] overflow-y-auto p-5 space-y-4">
              {toolCalls.length === 0 ? (
                <p className="text-slate-600 text-sm text-center mt-20">
                  RiskPulse evaluations will appear here when the agent triggers
                  a tool...
                </p>
              ) : (
                <AnimatePresence>
                  {toolCalls.map((tc, i) => {
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.4 }}
                        className={`border rounded-xl p-4 ${getToolColor(
                          tc.toolName
                        )}`}
                      >
                        {/* Tool Header */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4" />
                            <span className="font-mono text-xs font-bold uppercase">
                              {tc.toolName.replace(/_/g, " ")}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-500">
                            {tc.timestamp.toLocaleTimeString()}
                          </span>
                        </div>

                        {/* Args */}
                        <div className="bg-black/30 rounded-lg px-3 py-2 mb-3">
                          <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">
                            Parameters
                          </p>
                          <pre className="text-xs text-slate-300 whitespace-pre-wrap">
                            {JSON.stringify(tc.args, null, 2)}
                          </pre>
                        </div>

                        {/* Decision Badge */}
                        {tc.decision && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="flex items-center gap-2 mb-2"
                          >
                            <span className="text-[10px] uppercase tracking-wider text-slate-500">
                              Decision:
                            </span>
                            <span
                              className={`text-sm font-black ${getDecisionColor(tc.decision)}`}
                            >
                              {tc.decision}
                            </span>
                          </motion.div>
                        )}

                        {/* Explanation */}
                        {tc.explanation && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="bg-black/20 rounded-lg px-3 py-2 mt-2"
                          >
                            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 flex justify-between">
                              <span>Threat Analysis</span>
                              {tc.score != null && (
                                <span className={getDecisionColor(tc.decision || "")}>
                                  Score: {tc.score}
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-slate-300 leading-relaxed">
                              {tc.explanation}
                            </p>
                          </motion.div>
                        )}
                        
                        {/* Latency Footer */}
                        {tc.score != null && tc.moss_ms != null && tc.eval_ms != null && (
                          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-white/5 text-[9px] text-slate-500 uppercase tracking-wider font-mono">
                            <span className="flex items-center gap-1">
                              <Activity className="w-3 h-3 text-amber-500" />
                              Embed: {(tc.embed_ms ?? 0).toFixed(0)}ms
                            </span>
                            <span className="flex items-center gap-1">
                              <Zap className="w-3 h-3 text-cyan-500" />
                              Moss: {tc.moss_ms.toFixed(1)}ms
                            </span>
                            <span className="flex items-center gap-1">
                              <Cpu className="w-3 h-3 text-emerald-500" />
                              Engine: {tc.eval_ms.toFixed(1)}ms
                            </span>
                            <span className="ml-auto text-slate-400 font-semibold">
                              Total: {((tc.embed_ms ?? 0) + tc.moss_ms + tc.eval_ms).toFixed(1)}ms
                            </span>
                          </div>
                        )}

                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              )}
              <div ref={toolCallEndRef} />
            </div>
          </div>
        </div>

        {/* Bottom Info Bar */}
        <div className="mt-6 bg-[#0F0F11] border border-white/10 rounded-xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-400">Moss Retrieval Active</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-400">Risk Engine Online</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-400" : "bg-slate-600"}`} />
              <span className="text-xs text-slate-400">VAPI {isConnected ? "Connected" : "Disconnected"}</span>
            </div>
          </div>
          <div className="text-xs text-slate-600">
            12 Tools Active — All routed through RiskPulse
          </div>
        </div>
      </div>
    </div>
  );
}
