"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  Layers, 
  CheckCircle2, 
  RefreshCw,
  TrendingUp,
  AlertCircle,
  Search,
  ArrowUpRight,
  ShieldCheck,
  Filter,
  BarChart3
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [savingsData, setSavingsData] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [venn, setVenn] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAllRows, setShowAllRows] = useState(false);

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
      setSavingsData(savRes || []);
      setHeatmap(heatRes || []);
      setVenn(vennRes || null);
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

  // Filter & paginate savings table client-side for instant responsive interaction
  const filteredSavings = useMemo(() => {
    if (!savingsData) return [];
    let list = savingsData;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (row) =>
          row.cnmc_code?.toLowerCase().includes(q) ||
          row.material_description?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [savingsData, searchQuery]);

  const displayedSavings = useMemo(() => {
    if (showAllRows) return filteredSavings;
    return filteredSavings.slice(0, 10);
  }, [filteredSavings, showAllRows]);

  const totalConsolidatedVolume = useMemo(() => {
    return (savingsData || []).reduce((acc, curr) => acc + (curr.total_volume || 0), 0);
  }, [savingsData]);

  return (
    <div className="space-y-6 pb-10">
      {/* Executive Hero Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[11px] font-semibold tracking-wider text-emerald-400 uppercase">
              Harmonization Registry
            </span>
            <span className="text-zinc-600">|</span>
            <span className="text-[11px] text-zinc-400 font-medium">
              Multi-CPSE Consolidation Active
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Analytics & Collaborative Savings
          </h1>
          <p className="text-xs text-zinc-400 font-normal">
            Cross-CPSE procurement demand consolidation & price variance arbitration across CPCL, IOCL, and BPCL.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <Link
            href="/ingestion"
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/[0.08] rounded-xl text-xs font-medium apple-press transition"
          >
            <span>Ingestion Pipeline</span>
            <ArrowUpRight className="h-3.5 w-3.5 text-zinc-400" />
          </Link>

          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="flex items-center space-x-1.5 px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-semibold shadow-sm apple-press transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-black" : "text-black"}`} />
            <span>{loading ? "Refreshing..." : "Refresh Data"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-2xl flex items-center space-x-2.5">
          <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* TOP 4 HERO KPI CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* HERO CARD 1: Total Projected Savings (Elevated to #1) */}
        <div className="glass-card rounded-2xl p-5 space-y-3 relative overflow-hidden border border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 via-transparent to-transparent">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-emerald-400 uppercase">
              Projected Savings
            </span>
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            </div>
          </div>

          <div>
            <div className="text-2xl font-extrabold text-white font-mono tracking-tight">
              ₹{summary?.collaborative_savings_total_lakhs || 0} Lakhs
            </div>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Eliminating multi-vendor price spread
            </p>
          </div>

          <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px]">
            <span className="text-zinc-400">Consolidated Volume</span>
            <span className="text-white font-mono font-semibold">
              {totalConsolidatedVolume.toLocaleString()} units
            </span>
          </div>
        </div>

        {/* HERO CARD 2: Standardization Coverage */}
        <div className="glass-card rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Standardization
            </span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-200 border border-white/[0.08]">
              National {cov.National}%
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs text-zinc-300 mb-1.5 font-medium">
              <span>National Progress</span>
              <span className="font-bold text-white font-mono">{cov.National}%</span>
            </div>
            <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden border border-white/[0.06]">
              <div 
                className="bg-white h-full rounded-full transition-all duration-300" 
                style={{ width: `${Math.min(100, Math.max(0, cov.National))}%` }}
              ></div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-1.5 pt-1">
            <div className="p-2 rounded-lg bg-zinc-900/60 border border-white/[0.06] text-center">
              <span className="text-[9px] text-zinc-400 block">CPCL</span>
              <span className="text-xs font-bold text-white font-mono">{cov.CPCL}%</span>
            </div>
            <div className="p-2 rounded-lg bg-zinc-900/60 border border-white/[0.06] text-center">
              <span className="text-[9px] text-zinc-400 block">IOCL</span>
              <span className="text-xs font-bold text-white font-mono">{cov.IOCL}%</span>
            </div>
            <div className="p-2 rounded-lg bg-zinc-900/60 border border-white/[0.06] text-center">
              <span className="text-[9px] text-zinc-400 block">BPCL</span>
              <span className="text-xs font-bold text-white font-mono">{cov.BPCL}%</span>
            </div>
          </div>
        </div>

        {/* HERO CARD 3: Duplicate Breakdown */}
        <div className="glass-card rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Duplicate Breakdown
            </span>
            <Layers className="h-4 w-4 text-zinc-500" />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-zinc-400 block">Identical</span>
              <span className="text-sm font-bold text-emerald-400 font-mono mt-0.5 block">{dupes.identical.toLocaleString()}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-zinc-400 block">Near-Dupes</span>
              <span className="text-sm font-bold text-zinc-200 font-mono mt-0.5 block">{dupes.near_dupes.toLocaleString()}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-zinc-400 block">Substitutes</span>
              <span className="text-sm font-bold text-amber-400 font-mono mt-0.5 block">{dupes.substitutes.toLocaleString()}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-zinc-400 block">Resolved</span>
              <span className="text-sm font-bold text-white font-mono mt-0.5 block">{dupes.total_resolved.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* HERO CARD 4: Interactive Governance Review Queue */}
        <div className="glass-card rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Review Queue
            </span>
            <Link 
              href="/review" 
              className="text-[11px] text-zinc-400 hover:text-white flex items-center space-x-1 transition"
            >
              <span>Open</span>
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Link
              href="/review"
              className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition group"
            >
              <span className="text-[10px] text-emerald-400 block font-medium group-hover:underline">Pending (≥90%)</span>
              <span className="text-sm font-bold text-emerald-300 font-mono mt-0.5 block">{queue.pending_high}</span>
            </Link>
            <Link
              href="/review"
              className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition group"
            >
              <span className="text-[10px] text-amber-400 block font-medium group-hover:underline">Pending (70-89%)</span>
              <span className="text-sm font-bold text-amber-300 font-mono mt-0.5 block">{queue.pending_med}</span>
            </Link>
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-zinc-400 block font-medium">Approved</span>
              <span className="text-sm font-bold text-white font-mono mt-0.5 block">{queue.approved_today}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
              <span className="text-[10px] text-rose-400 block font-medium">Vetoed</span>
              <span className="text-sm font-bold text-rose-300 font-mono mt-0.5 block">{queue.rejected}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Demand Aggregation & Savings Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Demand Aggregation & Collaborative Savings
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Consolidated procurement volumes eliminating multi-vendor price variance across CPSEs.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
            {/* Real-time search filter */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search CNMC or description..."
                className="pl-8 pr-3 py-1.5 bg-zinc-900/80 border border-white/[0.08] rounded-xl text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-white/20 w-full sm:w-60"
              />
            </div>

            {/* Toggle Top 10 vs All */}
            {filteredSavings.length > 10 && (
              <button
                onClick={() => setShowAllRows(!showAllRows)}
                className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/[0.08] rounded-xl text-xs font-medium apple-press transition whitespace-nowrap"
              >
                {showAllRows ? "Show Top 10" : `View All (${filteredSavings.length})`}
              </button>
            )}

            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-mono whitespace-nowrap">
                Total Savings: ₹{summary?.collaborative_savings_total_lakhs || 0} Lakhs
              </span>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
              <tr>
                <th className="py-3 px-4">CNMC Code</th>
                <th className="py-3 px-4">Standardized Description (ISO 8000)</th>
                <th className="py-3 px-4 text-right">CPCL Vol</th>
                <th className="py-3 px-4 text-right">IOCL Vol</th>
                <th className="py-3 px-4 text-right">BPCL Vol</th>
                <th className="py-3 px-4 text-right">Total Vol</th>
                <th className="py-3 px-4 text-right">Price Variance</th>
                <th className="py-3 px-4 text-right text-emerald-400">Est. Savings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {displayedSavings && displayedSavings.length > 0 ? (
                displayedSavings.map((row) => (
                  <tr key={row.cnmc_code} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-zinc-200">{row.cnmc_code}</td>
                    <td className="py-3 px-4 font-medium text-zinc-100">{row.material_description}</td>
                    <td className="py-3 px-4 text-right text-zinc-300 font-mono">{row.cpcl_volume} {row.base_uom}</td>
                    <td className="py-3 px-4 text-right text-zinc-300 font-mono">{row.iocl_volume} {row.base_uom}</td>
                    <td className="py-3 px-4 text-right text-zinc-300 font-mono">{row.bpcl_volume} {row.base_uom}</td>
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
                  <td colSpan={8} className="py-8 text-center text-zinc-500">
                    {searchQuery ? "No matching records found for search query." : "No CNMC crosswalk records minted yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Grid: Heatmap, Overlap, Dedicated Taxonomy Distribution */}
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
                  <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div className="bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                      <span className="text-zinc-400 block text-[10px] font-medium">CPCL</span>
                      <span className="text-white font-mono font-semibold">{item.cpcl_pct}%</span>
                    </div>
                    <div className="bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                      <span className="text-zinc-400 block text-[10px] font-medium">IOCL</span>
                      <span className="text-white font-mono font-semibold">{item.iocl_pct}%</span>
                    </div>
                    <div className="bg-zinc-800/60 border border-white/[0.06] py-1 rounded-lg">
                      <span className="text-zinc-400 block text-[10px] font-medium">BPCL</span>
                      <span className="text-white font-mono font-semibold">{item.bpcl_pct}%</span>
                    </div>
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
                {venn ? (venn.all_three || 0).toLocaleString() : 0}
              </span>
              <span className="text-xs text-zinc-300 font-medium">Common to All 3 CPSEs</span>
            </div>

            <div className="pt-3 border-t border-white/[0.06] grid grid-cols-3 gap-2 text-[11px]">
              <div className="p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                <span className="text-zinc-400 block text-[10px]">CPCL & IOCL</span>
                <span className="font-mono font-bold text-white">{venn ? (venn.cpcl_iocl || 0).toLocaleString() : 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                <span className="text-zinc-400 block text-[10px]">IOCL & BPCL</span>
                <span className="font-mono font-bold text-white">{venn ? (venn.iocl_bpcl || 0).toLocaleString() : 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-zinc-950 border border-white/[0.04]">
                <span className="text-zinc-400 block text-[10px]">CPCL & BPCL</span>
                <span className="font-mono font-bold text-white">{venn ? (venn.cpcl_bpcl || 0).toLocaleString() : 0}</span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-zinc-500 text-center">
            Harmonization eliminates duplicate safety stock across plants.
          </div>
        </div>

        {/* Dedicated Material Group Taxonomy & Spend Distribution */}
        <div className="glass-card rounded-2xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
                Spend Taxonomy Breakdown
              </span>
              <BarChart3 className="h-4 w-4 text-zinc-500" />
            </div>

            <div className="space-y-2">
              {summary?.material_group_distribution && Object.keys(summary.material_group_distribution).length > 0 ? (
                Object.entries(summary.material_group_distribution).map(([groupName, pct]: [string, any]) => (
                  <div key={groupName} className="space-y-1">
                    <div className="flex justify-between text-[11px] text-zinc-300 font-medium">
                      <span>{groupName}</span>
                      <span className="font-mono text-zinc-200 font-semibold">{pct}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden border border-white/[0.04]">
                      <div
                        className="bg-emerald-500/80 h-full rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                      ></div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  Awaiting taxonomy classification.
                </div>
              )}
            </div>
          </div>

          {/* Clean system status footer badge */}
          <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-zinc-500 font-mono">
            <span className="flex items-center space-x-1">
              <ShieldCheck className="h-3 w-3 text-emerald-500" />
              <span>HNSW Vector Index</span>
            </span>
            <span>100% Invariant Guardrails</span>
          </div>
        </div>
      </div>
    </div>
  );
}

