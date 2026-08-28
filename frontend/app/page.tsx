"use client";

import { useState } from "react";
import { Shield, ShieldAlert, ShieldCheck, Activity, Cpu, Server, Clock, ChevronRight, AlertTriangle, UserCheck, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Home() {
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  // Sandbox State
  const [actionType, setActionType] = useState("TRANSFER_MONEY");
  const [amount, setAmount] = useState(5000);
  const [beneficiary, setBeneficiary] = useState("EXISTING");
  const [baselineRisk, setBaselineRisk] = useState(10);

  const showAmount = actionType === "TRANSFER_MONEY";
  const showBeneficiary = actionType === "TRANSFER_MONEY" || actionType === "ADD_BENEFICIARY";

  const runCustomScenario = async () => {
    setActiveScenario("custom");
    setLoading(true);
    setData(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/evaluate-custom`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action_type: actionType,
          amount: amount,
          beneficiary_status: beneficiary,
          baseline_risk: baselineRisk
        })
      });
      const result = await res.json();
      setData(result);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const runScenario = async (scenarioId: string) => {
    setActiveScenario(scenarioId);
    setLoading(true);
    setData(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/scenarios/${scenarioId}/run`, {
        method: "POST"
      });
      const result = await res.json();
      setData(result);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case "ALLOW": return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
      case "VERIFY": return "text-amber-400 border-amber-500/30 bg-amber-500/10";
      case "BLOCK": return "text-rose-500 border-rose-500/30 bg-rose-500/10";
      case "ESCALATE": return "text-purple-400 border-purple-500/30 bg-purple-500/10";
      default: return "text-gray-400 border-gray-500/30 bg-gray-500/10";
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
              <h1 className="font-bold text-lg tracking-tight text-white">RiskPulse</h1>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 font-medium">Zero-Latency Contextual Guardrails</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-emerald-400">System Online</span>
            </div>
            <div className="h-4 w-px bg-white/10"></div>
            <div className="flex items-center gap-2 text-slate-400">
              <Server className="w-4 h-4" /> Moss Retrieval Active
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Risk Sandbox Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-500" />
              Risk Sandbox Interactive Testing
            </h2>
            <p className="text-xs text-slate-400 mt-1">Dynamically inject parameters to test the deterministic Risk Engine</p>
          </div>
        </div>

        {/* Sandbox Form */}
        <div className="bg-[#111113] border border-white/5 rounded-2xl p-6 mb-10 shadow-2xl relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-emerald-500 to-emerald-900" />
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Action Type</label>
              <select 
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
                className="w-full bg-[#161618] border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
              >
                <option value="TRANSFER_MONEY">Transfer Money</option>
                <option value="CHANGE_PHONE">Change Phone Number</option>
                <option value="CHANGE_EMAIL">Change Email</option>
                <option value="ADD_BENEFICIARY">Add Beneficiary</option>
                <option value="RESET_PIN">Reset PIN</option>
                <option value="CLOSE_ACCOUNT">Close Account</option>
              </select>
            </div>

            {showAmount && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider flex justify-between">
                  <span>Transaction Amount</span>
                  <span className="text-emerald-400">${amount.toLocaleString()}</span>
                </label>
                <input 
                  type="range" 
                  min="0" max="100000" step="500"
                  value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>
            )}

            {showBeneficiary && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Beneficiary Status</label>
                <select 
                  value={beneficiary}
                  onChange={(e) => setBeneficiary(e.target.value)}
                  className="w-full bg-[#161618] border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="EXISTING">Existing Payee</option>
                  <option value="NEW">New (Untrusted)</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider flex justify-between">
                <span>Customer Baseline Risk</span>
                <span className="text-emerald-400">{baselineRisk}/100</span>
              </label>
              <input 
                type="range" 
                min="1" max="100" step="1"
                value={baselineRisk}
                onChange={(e) => setBaselineRisk(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <button 
              onClick={runCustomScenario}
              className="px-6 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20 transition-all font-semibold text-sm flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Inject Payload
            </button>
          </div>
        </div>

        {/* Scenarios Header (Existing Demo) */}
        <div className="flex items-center justify-between mb-8 mt-12 pt-8 border-t border-white/5">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-500" />
              Threat Vector Simulator
            </h2>
            <p className="text-xs text-slate-400 mt-1">Inject simulated telemetry to observe real-time RiskPulse evaluations</p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => runScenario("safe")}
              className="flex flex-col items-start px-4 py-2 rounded-md bg-[#161618] border border-white/5 hover:border-emerald-500/50 hover:bg-emerald-500/10 transition-all text-sm font-medium"
            >
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Inject Nominal Traffic
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-1 ml-6">ID: CUST_DEMO_SAFE</span>
            </button>
            <button 
              onClick={() => runScenario("suspicious")}
              className="flex flex-col items-start px-4 py-2 rounded-md bg-[#161618] border border-white/5 hover:border-amber-500/50 hover:bg-amber-500/10 transition-all text-sm font-medium"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Inject Anomalous Vector
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-1 ml-6">ID: CUST_DEMO_SUSP</span>
            </button>
            <button 
              onClick={() => runScenario("ato")}
              className="flex flex-col items-start px-4 py-2 rounded-md bg-[#161618] border border-white/5 hover:border-rose-500/50 hover:bg-rose-500/10 transition-all text-sm font-medium"
            >
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                Simulate Account Takeover
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-1 ml-6">ID: CUST_DEMO_ATO</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: Conversation */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <div className="bg-[#111113] border border-white/5 rounded-2xl p-5 flex-1 relative overflow-hidden group">
              <div className="flex items-center gap-2 mb-6 text-sm font-semibold text-slate-300">
                <Activity className="w-4 h-4 text-blue-400" />
                Intercepted Telemetry Stream
              </div>

              {!data && !loading && (
                <div className="h-40 flex items-center justify-center text-slate-500 text-sm">
                  Select a scenario to begin.
                </div>
              )}

              {loading && (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
                  <div className="relative w-12 h-12">
                    <div className="absolute inset-0 border-4 border-white/5 rounded-full"></div>
                    <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
                  </div>
                  <p className="text-sm font-medium animate-pulse">Intercepting Agent Communication...</p>
                </div>
              )}

              {data && data.detail && (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-rose-500">
                  <AlertTriangle className="w-8 h-8" />
                  <p className="text-sm font-medium">Error: Please ensure the backend is restarted. (API returned: {JSON.stringify(data.detail)})</p>
                </div>
              )}

              {data && data.action && (
                <AnimatePresence>
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col gap-6"
                  >
                    {/* Customer */}
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer</span>
                      <div className="bg-[#1C1C1F] p-3 rounded-lg rounded-tl-none border border-white/5 text-sm">
                        "{data.customer_request}"
                      </div>
                    </div>

                    {/* Proposed Action */}
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent Proposed Action</span>
                      <div className="bg-blue-500/5 border border-blue-500/20 p-3 rounded-lg text-xs font-mono text-blue-300">
                        <div className="flex justify-between mb-1"><span className="text-blue-500">ACTION:</span> <span>{data.action.action_type}</span></div>
                        <div className="flex justify-between mb-1"><span className="text-blue-500">AMOUNT:</span> <span>₹{data.action.amount}</span></div>
                        <div className="flex justify-between"><span className="text-blue-500">STATUS:</span> <span className="text-amber-400">{data.action.status}</span></div>
                      </div>
                    </div>

                    {/* RiskPulse Intercept */}
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 }}
                      className="flex items-center justify-center py-2"
                    >
                      <span className="text-xs font-medium px-3 py-1 bg-rose-500/10 text-rose-400 rounded-full border border-rose-500/20 flex items-center gap-2">
                        <Activity className="w-3 h-3" /> RiskPulse Intercepted
                      </span>
                    </motion.div>

                    {/* Final Response */}
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.8 }}
                      className="flex flex-col gap-1 items-end"
                    >
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Agent Final Response</span>
                      <div className="bg-indigo-600 p-3 rounded-lg rounded-tr-none text-sm text-white shadow-lg shadow-indigo-900/20">
                        {data.final_response}
                      </div>
                    </motion.div>

                  </motion.div>
                </AnimatePresence>
              )}
            </div>
          </div>

          {/* Center Panel: Risk Decision */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <div className="bg-[#121214] border border-white/5 rounded-xl p-5 shadow-2xl h-full flex flex-col">
              <div className="flex items-center gap-2 mb-6 pb-4 border-b border-white/5">
                <Shield className="w-5 h-5 text-rose-500" />
                <h3 className="font-semibold text-slate-200">Risk Evaluation Engine</h3>
              </div>
              
              {data && data.decision ? (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="flex-1 flex flex-col items-center justify-center gap-6"
                >
                  <div className="text-center">
                    <p className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-2">Risk Score</p>
                    <div className="relative inline-flex items-center justify-center">
                      <svg className="w-32 h-32 transform -rotate-90">
                        <circle cx="64" cy="64" r="60" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-white/5" />
                        <motion.circle 
                          initial={{ strokeDasharray: "0 400" }}
                          animate={{ strokeDasharray: `${(data.decision.risk_score / 100) * 377} 400` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          cx="64" cy="64" r="60" 
                          stroke="currentColor" strokeWidth="6" fill="transparent" 
                          strokeLinecap="round"
                          className={data.decision.risk_score > 80 ? "text-rose-500" : data.decision.risk_score > 40 ? "text-amber-500" : "text-emerald-500"} 
                        />
                      </svg>
                      <span className="absolute text-4xl font-bold text-white">{data.decision.risk_score}</span>
                    </div>
                  </div>

                  <div className={`w-full py-3 px-4 rounded-xl border text-center font-bold tracking-widest ${getDecisionColor(data.decision.decision)}`}>
                    {data.decision.decision}
                  </div>

                  <div className="w-full bg-[#1A1A1D] rounded-lg p-4 border border-white/5">
                    <p className="text-sm text-slate-300 leading-relaxed text-center">
                      {data.decision.explanation}
                    </p>
                  </div>

                  {data.decision.signals.length > 0 && (
                    <div className="w-full mt-2">
                      <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Key Signals</p>
                      <div className="flex flex-col gap-2">
                        {data.decision.signals.map((s: any, i: number) => (
                          <div key={i} className="flex justify-between items-center bg-white/5 rounded px-3 py-2 text-xs">
                            <span className="text-slate-300">{s.name}</span>
                            <span className={s.impact > 0 ? "text-rose-400 font-mono" : "text-emerald-400 font-mono"}>+{s.impact}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-slate-600">
                  <Shield className="w-16 h-16 opacity-20" />
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Moss Retrieval */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <div className="bg-[#121214] border border-white/5 rounded-xl p-5 shadow-2xl h-full flex flex-col">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Server className="w-5 h-5 text-purple-400" />
                  <h3 className="font-semibold text-slate-200">Moss Context</h3>
                </div>
                {data && (
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded border border-emerald-400/20">
                    ⚡ {data.moss_latency_ms} ms
                  </span>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {data && data.decision && data.decision.retrieved_context ? (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="flex flex-col gap-3"
                  >
                    <p className="text-xs font-semibold text-slate-500 mb-2">
                      {data.decision.retrieved_context.length} relevant context items found
                    </p>
                    
                    {data.decision.retrieved_context.map((ctx: any, i: number) => (
                      <div key={i} className="bg-[#1A1A1D] border border-white/5 rounded-lg p-3 hover:border-purple-500/30 transition-colors">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-[10px] uppercase font-bold text-purple-400 tracking-wider px-2 py-0.5 bg-purple-500/10 rounded">
                            {ctx.type}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">Relevance: {ctx.relevance}</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed line-clamp-4">
                          {ctx.content.replace(/\[METADATA:.*?\]\n/, '')}
                        </p>
                      </div>
                    ))}
                  </motion.div>
                ) : (
                  <div className="flex h-full items-center justify-center text-slate-600 text-sm text-center">
                    Context from semantic search will appear here.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Panel: Latency Timeline */}
        {data && data.decision && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-6 bg-[#121214] border border-white/5 rounded-xl p-5 shadow-2xl"
          >
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-emerald-400" />
              <h3 className="font-semibold text-slate-200">Execution Performance</h3>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-[#1A1A1D] p-4 rounded-lg border border-white/5">
                <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Moss Search</p>
                <p className="text-xl font-mono text-emerald-400">
                  {data.moss_latency_ms} <span className="text-sm text-emerald-400/50">ms</span>
                </p>
                <p className="text-[10px] text-slate-500 mt-1">{(data.moss_latency_ms / 1000).toFixed(2)} sec</p>
              </div>
              <div className="bg-[#1A1A1D] p-4 rounded-lg border border-white/5">
                <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Risk Logic</p>
                <p className="text-xl font-mono text-blue-400">
                  {data.risk_evaluation_latency_ms} <span className="text-sm text-blue-400/50">ms</span>
                </p>
                <p className="text-[10px] text-slate-500 mt-1">{(data.risk_evaluation_latency_ms / 1000).toFixed(4)} sec</p>
              </div>
              <div className="bg-[#1A1A1D] p-4 rounded-lg border border-white/5">
                <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Total Guardrail</p>
                <p className="text-xl font-mono text-rose-400">
                  {data.total_guardrail_latency_ms} <span className="text-sm text-rose-400/50">ms</span>
                </p>
                <p className="text-[10px] text-slate-500 mt-1">{(data.total_guardrail_latency_ms / 1000).toFixed(2)} sec</p>
              </div>
              <div className="bg-[#1A1A1D] p-4 rounded-lg border border-white/5">
                <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">LLM Response</p>
                <p className="text-xl font-mono text-amber-400">
                  {data.llm_latency_ms} <span className="text-sm text-amber-400/50">ms</span>
                </p>
                <p className="text-[10px] text-slate-500 mt-1">{(data.llm_latency_ms / 1000).toFixed(2)} sec</p>
              </div>
              <div className="bg-[#1A1A1D] p-4 rounded-lg border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.1)]">
                <p className="text-xs text-cyan-500 uppercase tracking-widest mb-1">Total Time</p>
                <p className="text-2xl font-mono text-cyan-400">
                  {((data.total_guardrail_latency_ms + data.llm_latency_ms) / 1000).toFixed(2)} <span className="text-sm text-cyan-400/50">sec</span>
                </p>
                <p className="text-[10px] text-slate-400 mt-1 leading-tight">Guardrail + LLM Inference</p>
              </div>
            </div>
          </motion.div>
        )}
      </main>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
      `}} />
    </div>
  );
}
