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
} from "lucide-react";

interface TranscriptEntry {
  role: "assistant" | "user" | "system";
  text: string;
  timestamp: Date;
}

interface ToolCallEvent {
  toolName: string;
  args: Record<string, unknown>;
  result?: string;
  decision?: string;
  score?: number;
  explanation?: string;
  moss_ms?: number;
  eval_ms?: number;
  timestamp: Date;
}

export default function VoiceAgentPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [callDuration, setCallDuration] = useState(0);
  const [textInput, setTextInput] = useState("");

  const vapiRef = useRef<any>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const toolCallEndRef = useRef<HTMLDivElement>(null);

  const VAPI_PUBLIC_KEY = "7126f1a4-bbb8-47b9-8264-252c6d21f175";
  const ASSISTANT_ID = "e6f879b5-b9e5-403a-831a-64500dda7057";

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  useEffect(() => {
    toolCallEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [toolCalls]);

  // Poll backend for latest evaluations while connected
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    if (isConnected) {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch("http://localhost:8000/api/vapi/latest-evaluations");
          const data = await res.json();
          if (data.evaluations && data.evaluations.length > 0) {
            setToolCalls(data.evaluations.map((ev: any) => ({
              toolName: ev.toolName,
              args: ev.args,
              result: ev.result,
              decision: ev.decision,
              explanation: ev.explanation,
              timestamp: new Date(ev.timestamp)
            })));
          }
        } catch (e) {
          console.error("Failed to fetch evaluations", e);
        }
      }, 1000);
    }
    return () => clearInterval(pollInterval);
  }, [isConnected]);

  // Call duration timer
  useEffect(() => {
    if (isConnected) {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isConnected]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const sendTextMessage = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || !vapiRef.current) return;

    vapiRef.current.send({
      type: "add-message",
      message: {
        role: "user",
        content: textInput
      }
    });
    setTextInput("");
  }, [textInput]);

  const startCall = useCallback(async () => {
    setIsConnecting(true);
    setTranscript([]);
    setToolCalls([]);

    try {
      const Vapi = (await import("@vapi-ai/web")).default;
      const vapi = new Vapi(VAPI_PUBLIC_KEY);
      vapiRef.current = vapi;

      vapi.on("call-start", () => {
        setIsConnected(true);
        setIsConnecting(false);
        setTranscript((prev) => [
          ...prev,
          {
            role: "system",
            text: "Call connected to RiskPulse Voice Agent",
            timestamp: new Date(),
          },
        ]);
      });

      vapi.on("call-end", () => {
        setIsConnected(false);
        setIsConnecting(false);
        setTranscript((prev) => [
          ...prev,
          {
            role: "system",
            text: "Call ended",
            timestamp: new Date(),
          },
        ]);
        vapiRef.current = null;
      });

      vapi.on("message", (msg: any) => {
        // Handle transcript messages
        if (msg.type === "transcript" && msg.transcriptType === "final") {
          setTranscript((prev) => [
            ...prev,
            {
              role: msg.role === "assistant" ? "assistant" : "user",
              text: msg.transcript,
              timestamp: new Date(),
            },
          ]);
        }

        // Handle tool calls
        if (msg.type === "tool-calls") {
          for (const tc of msg.toolCalls || []) {
            const fn = tc.function || {};
            setToolCalls((prev) => [
              ...prev,
              {
                toolName: fn.name || "unknown",
                args: fn.arguments || {},
                timestamp: new Date(),
              },
            ]);
          }
        }

        // Handle tool call results
        if (msg.type === "tool-calls-result") {
          for (const result of msg.toolCallResult || []) {
            setToolCalls((prev) => {
              const updated = [...prev];
              // Find the last tool call without a result and update it
              for (let i = updated.length - 1; i >= 0; i--) {
                if (!updated[i].result) {
                  updated[i] = { ...updated[i], result: result.result };
                  break;
                }
              }
              return updated;
            });
          }
        }
      });

      vapi.on("volume-level", (level: number) => {
        setVolumeLevel(level);
      });

      vapi.on("error", (err: any) => {
        console.error("VAPI Error:", err);
        setIsConnecting(false);
        setTranscript((prev) => [
          ...prev,
          {
            role: "system",
            text: `Error: ${err?.message || "Connection failed"}`,
            timestamp: new Date(),
          },
        ]);
      });

      await vapi.start(ASSISTANT_ID);
    } catch (err) {
      console.error("Failed to start call:", err);
      setIsConnecting(false);
    }
  }, []);

  const endCall = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.stop();
      vapiRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  const toggleMute = useCallback(() => {
    if (vapiRef.current) {
      const newMuted = !isMuted;
      vapiRef.current.setMuted(newMuted);
      setIsMuted(newMuted);
    }
  }, [isMuted]);

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
                className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-2xl shadow-emerald-500/30 cursor-pointer transition-all hover:shadow-emerald-500/50"
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
                  className={`w-14 h-14 rounded-full flex items-center justify-center cursor-pointer transition-all ${
                    isMuted
                      ? "bg-amber-500/20 border border-amber-500/30"
                      : "bg-white/10 border border-white/20 hover:bg-white/15"
                  }`}
                >
                  {isMuted ? (
                    <MicOff className="w-6 h-6 text-amber-400" />
                  ) : (
                    <Mic className="w-6 h-6 text-white" />
                  )}
                </motion.button>

                <motion.div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-2xl shadow-emerald-500/30 relative">
                  {/* Volume indicator */}
                  <motion.div
                    className="absolute inset-0 rounded-full bg-emerald-400/20"
                    animate={{
                      scale: 1 + volumeLevel * 0.3,
                      opacity: volumeLevel * 0.5,
                    }}
                    transition={{ duration: 0.1 }}
                  />
                  <Waves className="w-10 h-10 text-white relative z-10" />
                </motion.div>

                <motion.button
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

        {!isConnected && !isConnecting && transcript.length === 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-slate-500 text-sm mb-8"
          >
            Press the button above to start a live voice call with the RiskPulse
            AI Banking Agent
          </motion.p>
        )}

        {/* Two-column layout: Transcript + RiskPulse Events */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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

            {/* Chat Input */}
            {isConnected && (
              <div className="p-4 border-t border-white/10 bg-black/20">
                <form onSubmit={sendTextMessage} className="flex gap-2">
                  <input
                    type="text"
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Type Customer ID (e.g. C123456) or message..."
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-rose-500/50"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    Send
                  </button>
                </form>
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
                              {tc.score !== undefined && (
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
                        {tc.moss_ms !== undefined && tc.eval_ms !== undefined && (
                          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-white/5 text-[9px] text-slate-500 uppercase tracking-wider font-mono">
                            <span className="flex items-center gap-1">
                              <Zap className="w-3 h-3 text-cyan-500" />
                              Moss: {tc.moss_ms.toFixed(1)}ms
                            </span>
                            <span className="flex items-center gap-1">
                              <Cpu className="w-3 h-3 text-emerald-500" />
                              Engine: {tc.eval_ms.toFixed(1)}ms
                            </span>
                            <span className="ml-auto text-slate-400 font-semibold">
                              Total: {(tc.moss_ms + tc.eval_ms).toFixed(1)}ms
                            </span>
                          </div>
                        )}

                        {!tc.result && !tc.explanation && (
                          <div className="flex items-center gap-2 mt-2">
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{
                                duration: 1,
                                repeat: Infinity,
                                ease: "linear",
                              }}
                              className="w-3 h-3 border border-t-transparent border-current rounded-full"
                            />
                            <span className="text-xs">
                              Evaluating through RiskPulse...
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
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-400">VAPI Connected</span>
            </div>
          </div>
          <div className="text-xs text-slate-600">
            10 Tools Active — All routed through RiskPulse
          </div>
        </div>
      </div>
    </div>
  );
}
