"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  Layers, 
  CheckCircle2, 
  RefreshCw,
  Zap,
  ShieldCheck,
  AlertCircle
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [savingsData, setSavingsData] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [venn, setVenn] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, savRes, heatRes, vennRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getDemandSavings(),
        api.getQualityHeatmap(),
        api.getVennOverlap(),
      ]);

      setSummary(sumRes);
      setSavingsData(savRes);
      setHeatmap(heatRes);
      setVenn(vennRes);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load dynamic metrics from backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleTriggerMatching = async () => {
    setTriggering(true);
    try {
      await api.triggerMatching();
      await loadDashboardData();
    } catch (err: any) {
      alert(`Matching execution notice: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  };

  const cov = summary?.standardization_coverage || {
    National: 0.0,
    CPCL: 0.0,
    IOCL: 0.0,
    BPCL: 0.0
  };

  const dupes = summary?.duplicate_detection || {
    identical: 0,
    near_dupes: 0,
    substitutes: 0,
    total_resolved: 0
  };

  const queue = summary?.review_queue_counts || {
    pending_high: 0,
    pending_med: 0,
    approved_today: 0,
    rejected: 0
  };

  return (
    <div className="space-y-6">
      {/* Apple-style Hero Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            <span className="text-[11px] font-medium tracking-wide text-zinc-400 uppercase">
              Harmonization Registry
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Analytics & Collaborative Savings
          </h1>
          <p className="text-xs text-zinc-400 font-normal">
            Zero-training multi-CPSE demand consolidation across enterprise partners (CPCL, IOCL, BPCL & national CPSEs).
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={handleTriggerMatching}
            disabled={triggering}
            className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-semibold shadow-sm apple-press disabled:opacity-50 transition"
          >
            <Zap className="h-3.5 w-3.5 text-black" />
            <span>{triggering ? "Evaluating Invariants..." : "Run Matcher"}</span>
          </button>

          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-2xl flex items-center space-x-2.5">
          <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top 3 KPI Grid Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Standardization Coverage */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Standardization Coverage
            </span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-200 border border-white/[0.08]">
              National {cov.National}%
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-zinc-300 mb-1.5 font-medium">
                <span>National Aggregation</span>
                <span className="font-bold text-white">{cov.National}%</span>
              </div>
              <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden border border-white/[0.06]">
                <div className="bg-white h-full rounded-full transition-all duration-300" style={{ width: `${Math.min(100, Math.max(0, cov.National))}%` }}></div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              {Object.entries(cov)
                .filter(([key]) => key !== "National")
                .map(([org, pct]: [string, any]) => (
                  <div key={org} className="flex-1 min-w-[75px] p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06] text-center">
                    <span className="text-[10px] text-zinc-400 block font-medium">{org}</span>
                    <span className="text-sm font-bold text-white font-mono">{pct}%</span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Duplicate Detection Summary */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Duplicate Breakdown
            </span>
            <Layers className="h-4 w-4 text-zinc-500" />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-zinc-400 block">Identical</span>
              <span className="text-base font-bold text-emerald-400 font-mono mt-0.5 block">{dupes.identical.toLocaleString()}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-zinc-400 block">Near-Duplicates</span>
              <span className="text-base font-bold text-zinc-200 font-mono mt-0.5 block">{dupes.near_dupes.toLocaleString()}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-zinc-400 block">Substitutes</span>
              <span className="text-base font-bold text-amber-400 font-mono mt-0.5 block">{dupes.substitutes.toLocaleString()}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-zinc-400 block">Total Resolved</span>
              <span className="text-base font-bold text-white font-mono mt-0.5 block">{dupes.total_resolved.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Review Queue Status */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Governance Review Queue
            </span>
            <CheckCircle2 className="h-4 w-4 text-zinc-500" />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-emerald-400 block font-medium">Pending High (≥90%)</span>
              <span className="text-base font-bold text-emerald-300 font-mono mt-0.5 block">{queue.pending_high}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-amber-400 block font-medium">Pending Med (70-89%)</span>
              <span className="text-base font-bold text-amber-300 font-mono mt-0.5 block">{queue.pending_med}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-zinc-300 block font-medium">Approved</span>
              <span className="text-base font-bold text-white font-mono mt-0.5 block">{queue.approved_today}</span>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[11px] text-rose-400 block font-medium">Rejected / Vetoed</span>
              <span className="text-base font-bold text-rose-300 font-mono mt-0.5 block">{queue.rejected}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Demand Aggregation & Savings Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Demand Aggregation & Collaborative Savings
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Consolidated procurement volumes eliminating multi-vendor price variance across CPSEs.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-mono">
              Total Savings: ₹{summary?.collaborative_savings_total_lakhs || 0} Lakhs
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
              <tr>
                <th className="py-3 px-4">CNMC Code</th>
                <th className="py-3 px-4">Standardized Description (ISO 8000)</th>
                <th className="py-3 px-4 text-right">Enterprise Breakdown</th>
                <th className="py-3 px-4 text-right">Total Vol</th>
                <th className="py-3 px-4 text-right">Price Variance</th>
                <th className="py-3 px-4 text-right text-emerald-400">Est. Savings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {savingsData && savingsData.length > 0 ? (
                savingsData.map((row) => (
                  <tr key={row.cnmc_code} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-zinc-200">{row.cnmc_code}</td>
                    <td className="py-3 px-4 font-medium text-zinc-100">{row.material_description}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex flex-wrap justify-end gap-1.5">
                        {row.organization_volumes && Object.keys(row.organization_volumes).length > 0 ? (
                          Object.entries(row.organization_volumes).map(([org, vol]) => (
                            <span key={org} className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-800/80 text-zinc-300 border border-white/[0.06]">
                              <span className="font-semibold text-white mr-1">{org}:</span> {vol} {row.base_uom}
                            </span>
                          ))
                        ) : (
                          <span className="text-zinc-400 font-mono text-xs">{row.total_volume} {row.base_uom}</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-white font-mono">{row.total_volume} {row.base_uom}</td>
                    <td className="py-3 px-4 text-right text-zinc-400 font-mono">
                      ₹{row.min_price?.toLocaleString() || 0} - ₹{row.max_price?.toLocaleString() || 0}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-emerald-400 font-mono">
                      ₹{row.estimated_savings_lakhs} Lakhs
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-zinc-500">
                    No CNMC crosswalk records minted yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Grid: Heatmap, Overlap, Health */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Specification Completeness */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Specification Completeness
            </span>
          </div>

          <div className="space-y-2.5">
            {heatmap && heatmap.length > 0 ? (
              heatmap.map((item) => (
                <div key={item.field_name} className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
                  <div className="text-xs font-medium text-zinc-300 mb-2">{item.field_name}</div>
                  <div className="flex flex-wrap gap-2 text-center text-[11px]">
                    {item.cpse_scores && Object.keys(item.cpse_scores).length > 0 ? (
                      Object.entries(item.cpse_scores).map(([org, pct]: [string, any]) => (
                        <div key={org} className="flex-1 min-w-[60px] bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                          <span className="text-zinc-400 block text-[10px] font-medium">{org}</span>
                          <span className="text-white font-mono font-semibold">{pct}%</span>
                        </div>
                      ))
                    ) : (
                      <>
                        <div className="flex-1 bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                          <span className="text-zinc-400 block text-[10px] font-medium">CPCL</span>
                          <span className="text-white font-mono font-semibold">{item.cpcl_pct || 0}%</span>
                        </div>
                        <div className="flex-1 bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                          <span className="text-zinc-400 block text-[10px] font-medium">IOCL</span>
                          <span className="text-white font-mono font-semibold">{item.iocl_pct || 0}%</span>
                        </div>
                        <div className="flex-1 bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                          <span className="text-zinc-400 block text-[10px] font-medium">BPCL</span>
                          <span className="text-white font-mono font-semibold">{item.bpcl_pct || 0}%</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-xs text-zinc-500">
                Awaiting specification data ingestion.
              </div>
            )}
          </div>
        </div>

        {/* 3-Way Overlap Card */}
        <div className="glass-card rounded-2xl p-5 space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Multi-CPSE Overlap
            </span>
          </div>

          <div className="p-5 bg-zinc-900/70 rounded-xl border border-white/[0.06] text-center space-y-3">
            <div>
              <span className="text-2xl font-bold tracking-tight text-white font-mono block">
                {venn ? (venn.multi_cpse_clusters || venn.all_three || 0).toLocaleString() : 0}
              </span>
              <span className="text-xs text-zinc-300 font-medium">Multi-CPSE Harmonized Clusters</span>
            </div>

            <div className="pt-3 border-t border-white/[0.06] flex flex-wrap gap-2 text-[11px]">
              {venn?.pairwise_overlap && Object.keys(venn.pairwise_overlap).length > 0 ? (
                Object.entries(venn.pairwise_overlap).slice(0, 3).map(([pair, count]: [string, any]) => (
                  <div key={pair} className="flex-1 min-w-[80px] p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px] truncate">{pair.replace("_", " & ")}</span>
                    <span className="font-mono font-bold text-white">{count}</span>
                  </div>
                ))
              ) : (
                <>
                  <div className="flex-1 p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">CPCL & IOCL</span>
                    <span className="font-mono font-bold text-white">{venn ? (venn.cpcl_iocl || 0).toLocaleString() : 0}</span>
                  </div>
                  <div className="flex-1 p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">IOCL & BPCL</span>
                    <span className="font-mono font-bold text-white">{venn ? (venn.iocl_bpcl || 0).toLocaleString() : 0}</span>
                  </div>
                  <div className="flex-1 p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">CPCL & BPCL</span>
                    <span className="font-mono font-bold text-white">{venn ? (venn.cpcl_bpcl || 0).toLocaleString() : 0}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="text-[11px] text-zinc-500 text-center">
            Harmonization eliminates duplicate safety stock across plants.
          </div>
        </div>

        {/* Engine Status */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Engine Health
            </span>
            <ShieldCheck className="h-4 w-4 text-zinc-400" />
          </div>

          <div className="space-y-2.5">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06] space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-zinc-400">Embedding</span>
                <span className="text-zinc-200 font-medium font-mono">all-MiniLM-L6-v2</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">pgvector Index</span>
                <span className="text-zinc-200 font-medium font-mono">HNSW Sub-50ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Guardrails</span>
                <span className="text-zinc-200 font-medium">100% Invariant Veto</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/60 border border-white/[0.06] space-y-2 text-xs">
              <span className="font-semibold text-zinc-300 block text-[11px]">Material Group Taxonomy:</span>
              <div className="space-y-1 text-[11px] text-zinc-400">
                {summary?.material_group_distribution && Object.keys(summary.material_group_distribution).length > 0 ? (
                  Object.entries(summary.material_group_distribution).map(([groupName, pct]: [string, any]) => (
                    <div key={groupName} className="flex justify-between">
                      <span>{groupName}</span>
                      <span className="text-zinc-200 font-mono font-semibold">{pct}%</span>
                    </div>
                  ))
                ) : (
                  <div className="text-zinc-500 text-[10px] py-1">Awaiting taxonomy classification.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
