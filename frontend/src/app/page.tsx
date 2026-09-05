"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  RefreshCw,
  AlertCircle,
  Search,
  ArrowRight,
  TrendingUp,
  Layers,
  GitMerge
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [savingsData, setSavingsData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAllRows, setShowAllRows] = useState(false);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, savRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getDemandSavings(),
      ]);

      setSummary(sumRes);
      setSavingsData(savRes || []);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load metrics from backend");
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

  const totalDuplicatesResolved = (dupes.identical || 0) + (dupes.near_dupes || 0);

  // Client-side search & pagination for responsiveness
  const filteredDemand = useMemo(() => {
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

  const displayedDemand = useMemo(() => {
    if (showAllRows) return filteredDemand;
    return filteredDemand.slice(0, 10);
  }, [filteredDemand, showAllRows]);

  const totalConsolidatedVolume = useMemo(() => {
    return (savingsData || []).reduce((acc, curr) => acc + (curr.total_volume || 0), 0);
  }, [savingsData]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Executive Hero Surface */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              National Harmonization Framework
            </span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            Analytics & Procurement Overview
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-2xl leading-relaxed">
            Multi-enterprise catalog standardization across CPCL, IOCL, BPCL, ONGC, NTPC, SAIL, BHEL, and Coal India.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <Link
            href="/ingestion"
            className="flex items-center space-x-1.5 h-8.5 px-3.5 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-950 rounded-xl text-xs font-semibold apple-press transition shadow-sm"
          >
            <span>Import Extract</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>

          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="flex items-center space-x-1.5 h-8.5 px-3 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs font-medium apple-press transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/30 text-red-700 dark:text-red-300 text-xs rounded-xl flex items-center space-x-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* TOP 3 GLANCEABLE APPLE-STYLE KPI CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* KPI 1: National Standardization Rate */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Standardization Progress
            </span>
            <TrendingUp className="h-4 w-4 text-zinc-400" />
          </div>

          <div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
                {cov.National}%
              </span>
              <span className="text-xs text-zinc-500 font-medium">National Coverage</span>
            </div>

            <div className="w-full bg-zinc-200/80 dark:bg-zinc-800 h-2 rounded-full overflow-hidden mt-3">
              <div 
                className="bg-zinc-900 dark:bg-zinc-100 h-full rounded-full transition-all duration-500" 
                style={{ width: `${Math.min(100, Math.max(0, cov.National))}%` }}
              />
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-xs text-zinc-500 font-mono">
            {Object.entries(cov)
              .filter(([key]) => key !== "National")
              .slice(0, 3)
              .map(([org, pct]: [string, any]) => (
                <span key={org}>
                  <strong className="text-zinc-800 dark:text-zinc-200">{org}:</strong> {pct}%
                </span>
              ))}
          </div>
        </div>

        {/* KPI 2: Duplicates Resolved */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Duplicates Resolved
            </span>
            <Layers className="h-4 w-4 text-zinc-400" />
          </div>

          <div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
                {totalDuplicatesResolved.toLocaleString()}
              </span>
              <span className="text-xs text-zinc-500 font-medium">Harmonized</span>
            </div>

            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed">
              Consolidated from {dupes.total_resolved.toLocaleString()} catalog records across 8 participating CPSEs.
            </p>
          </div>

          <div className="pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-xs text-zinc-500 font-mono">
            <span>Identical: <strong className="text-zinc-800 dark:text-zinc-200">{dupes.identical}</strong></span>
            <span>Near-Dupes: <strong className="text-zinc-800 dark:text-zinc-200">{dupes.near_dupes}</strong></span>
            <span>Substitutes: <strong className="text-zinc-800 dark:text-zinc-200">{dupes.substitutes}</strong></span>
          </div>
        </div>

        {/* KPI 3: Review Queue Status */}
        <div className="glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Governance Queue
            </span>
            <GitMerge className="h-4 w-4 text-zinc-400" />
          </div>

          <div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
                {queue.pending_high + queue.pending_med}
              </span>
              <span className="text-xs text-zinc-500 font-medium">Pending Review</span>
            </div>

            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed">
              {queue.approved_today} approved today · {queue.rejected} vetoed under safety invariants.
            </p>
          </div>

          <div className="pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-xs">
            <Link 
              href="/review" 
              className="text-xs font-medium text-zinc-900 dark:text-zinc-100 hover:underline flex items-center space-x-1"
            >
              <span>Inspect Match Queue</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
            <span className="text-[11px] font-mono text-zinc-400">
              {queue.pending_high} High-Conf
            </span>
          </div>
        </div>
      </div>

      {/* Demand Aggregation & Catalog Consolidation Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              Demand Aggregation & Consolidated Sourcing
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Consolidated procurement volumes across participating CPSEs for strategic bulk sourcing.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            {/* Search Filter */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter CNMC or description..."
                className="pl-8 pr-3 h-8 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-900 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:border-zinc-400 w-56"
              />
            </div>

            {filteredDemand.length > 10 && (
              <button
                onClick={() => setShowAllRows(!showAllRows)}
                className="h-8 px-3 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-medium apple-press transition"
              >
                {showAllRows ? "Top 10" : `View All (${filteredDemand.length})`}
              </button>
            )}

            <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 whitespace-nowrap">
              Volume: <strong className="text-zinc-900 dark:text-zinc-100 font-semibold">{totalConsolidatedVolume.toLocaleString()} Units</strong>
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-700 dark:text-zinc-300">
            <thead className="bg-zinc-50 dark:bg-zinc-950/60 text-zinc-500 uppercase font-medium border-b border-zinc-200 dark:border-zinc-800 text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4 font-mono">National CNMC</th>
                <th className="py-3 px-4">Harmonized Specification (ISO 8000)</th>
                <th className="py-3 px-4 text-right">Enterprise Volumes</th>
                <th className="py-3 px-4 text-right">Consolidated Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200/70 dark:divide-zinc-800/70">
              {displayedDemand.map((row) => (
                <tr key={row.cnmc_code} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-zinc-900 dark:text-zinc-100 whitespace-nowrap">
                    {row.cnmc_code}
                  </td>
                  <td className="py-3.5 px-4 font-sans text-zinc-800 dark:text-zinc-200 leading-relaxed max-w-md">
                    {row.material_description}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex flex-wrap justify-end gap-1 font-mono text-[10px]">
                      {row.organization_volumes && Object.keys(row.organization_volumes).length > 0 ? (
                        Object.entries(row.organization_volumes).map(([org, vol]) => (
                          <span key={org} className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                            {org}: {vol} {row.base_uom}
                          </span>
                        ))
                      ) : (
                        <span className="text-zinc-500">{row.total_volume} {row.base_uom}</span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono font-semibold text-zinc-900 dark:text-zinc-100 tabular-nums">
                    {row.total_volume} {row.base_uom}
                  </td>
                </tr>
              ))}
              {displayedDemand.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-zinc-400 font-sans text-xs">
                    {searchQuery ? "No records matched your search query." : "No demand records registered yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
