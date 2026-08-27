"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/analytics`)
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => console.error(e));
  }, []);

  if (!data) return <div className="p-8 text-white">Loading...</div>;

  const chartData = [
    { name: "ALLOW", count: data.allow_count, color: "#10b981" },
    { name: "VERIFY", count: data.verify_count, color: "#f59e0b" },
    { name: "BLOCK", count: data.block_count, color: "#f43f5e" },
    { name: "ESCALATE", count: data.escalate_count, color: "#a855f7" }
  ];

  return (
    <div className="p-8 text-slate-200">
      <h2 className="text-2xl font-bold text-white mb-6">Risk Analytics</h2>
      
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div className="bg-[#121214] p-5 rounded-xl border border-white/5">
          <p className="text-sm text-slate-500 uppercase">Total Actions</p>
          <p className="text-3xl font-bold">{data.total_evaluated}</p>
        </div>
        <div className="bg-[#121214] p-5 rounded-xl border border-white/5 border-b-4 border-b-emerald-500">
          <p className="text-sm text-slate-500 uppercase">Allowed</p>
          <p className="text-3xl font-bold">{data.allow_count}</p>
        </div>
        <div className="bg-[#121214] p-5 rounded-xl border border-white/5 border-b-4 border-b-amber-500">
          <p className="text-sm text-slate-500 uppercase">Verified</p>
          <p className="text-3xl font-bold">{data.verify_count}</p>
        </div>
        <div className="bg-[#121214] p-5 rounded-xl border border-white/5 border-b-4 border-b-rose-500">
          <p className="text-sm text-slate-500 uppercase">Blocked</p>
          <p className="text-3xl font-bold">{data.block_count}</p>
        </div>
        <div className="bg-[#121214] p-5 rounded-xl border border-white/5 border-b-4 border-b-purple-500">
          <p className="text-sm text-slate-500 uppercase">Escalated</p>
          <p className="text-3xl font-bold">{data.escalate_count}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#121214] p-6 rounded-xl border border-white/5">
          <h3 className="text-lg font-semibold mb-6">Decision Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="name" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff'}} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#121214] p-6 rounded-xl border border-white/5">
          <h3 className="text-lg font-semibold mb-6">Average Latency (ms)</h3>
          <div className="flex flex-col gap-6">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Moss Retrieval</span>
                <span className="text-sm font-mono text-emerald-400">{data.avg_moss_latency_ms} ms</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div className="bg-emerald-400 h-2 rounded-full" style={{ width: '15%' }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium">Total Guardrail Decision</span>
                <span className="text-sm font-mono text-rose-400">{data.avg_guardrail_latency_ms} ms</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div className="bg-rose-400 h-2 rounded-full" style={{ width: '30%' }}></div>
              </div>
            </div>
          </div>
          
          <h3 className="text-lg font-semibold mb-4 mt-8">Recent High Risk Events</h3>
          <div className="flex flex-col gap-2">
            {data.recent_high_risk.map((ev: any, i: number) => (
              <div key={i} className="flex justify-between items-center p-3 bg-white/5 rounded-lg border border-rose-500/20">
                <div>
                  <p className="text-sm font-medium">{ev.type}</p>
                  <p className="text-xs text-slate-500">{ev.id}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-rose-400">Score: {ev.score}</span>
                  <span className="text-xs px-2 py-1 bg-rose-500/20 text-rose-400 rounded uppercase">{ev.decision}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
