export default function ArchitecturePage() {
  return (
    <div className="p-8 text-slate-200 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold text-white mb-8">System Architecture</h2>
      
      <div className="bg-[#121214] p-8 rounded-xl border border-white/5 mb-8">
        <h3 className="text-xl font-semibold mb-6 text-purple-400">The Problem: AI Agent Safety</h3>
        <p className="mb-4 leading-relaxed text-slate-300">
          When AI agents perform actions on behalf of customers (like transferring money or changing credentials), they lack the context required to make secure decisions. Traditional fraud engines are often disconnected from the conversational layer, leading to latency and disjointed user experiences.
        </p>
      </div>

      <div className="bg-[#121214] p-8 rounded-xl border border-white/5 mb-8">
        <h3 className="text-xl font-semibold mb-6 text-emerald-400">The Solution: RiskPulse Flow</h3>
        
        <div className="flex flex-col gap-2 font-mono text-sm mb-6 bg-[#0a0a0b] p-6 rounded-lg border border-white/10">
          <div className="text-slate-300">1. <span className="text-blue-400">AI Agent</span> proposes an action based on customer chat.</div>
          <div className="text-slate-500 pl-4">↓</div>
          <div className="text-slate-300">2. <span className="text-rose-400">RiskPulse</span> intercepts the action before execution.</div>
          <div className="text-slate-500 pl-4">↓</div>
          <div className="text-slate-300">3. <span className="text-emerald-400">Moss Semantic Search</span> retrieves related policies, events, and historical fraud cases in &lt; 10ms.</div>
          <div className="text-slate-500 pl-4">↓</div>
          <div className="text-slate-300">4. <span className="text-amber-400">Risk Engine</span> evaluates the action against the retrieved context deterministically.</div>
          <div className="text-slate-500 pl-4">↓</div>
          <div className="text-slate-300">5. Guardrail returns <span className="font-bold text-white">ALLOW / VERIFY / BLOCK / ESCALATE</span>.</div>
          <div className="text-slate-500 pl-4">↓</div>
          <div className="text-slate-300">6. <span className="text-blue-400">AI Agent</span> generates a safe response reflecting the decision.</div>
        </div>
      </div>

      <div className="bg-[#121214] p-8 rounded-xl border border-white/5">
        <h3 className="text-xl font-semibold mb-4 text-blue-400">Why Moss?</h3>
        <p className="leading-relaxed text-slate-300">
          Moss provides real-time, low-latency semantic retrieval that is co-located with the application logic. This allows RiskPulse to query unstructured contextual data (such as complex policy texts and rich historical fraud narratives) synchronously during the agent's action loop without introducing the latency overhead of a traditional remote Vector Database. The guardrail decision must be made in milliseconds so the AI feels natural and responsive.
        </p>
      </div>
    </div>
  );
}
