"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { 
  GitMerge, 
  CheckCircle2, 
  XCircle, 
  Split, 
  ShieldCheck, 
  ShieldAlert, 
  Check,
  RefreshCw
} from "lucide-react";

export default function ReviewQueuePage() {
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [clusterCard, setClusterCard] = useState<any>(null);
  const [goldenDesc, setGoldenDesc] = useState<string>("");
  const [reviewerNotes, setReviewerNotes] = useState<string>("");
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const items = await api.getReviewQueue("PENDING");
      setQueueItems(items);
      if (items.length > 0 && !selectedClusterId) {
        setSelectedClusterId(items[0].cluster_group_id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  useEffect(() => {
    if (selectedClusterId) {
      loadClusterDetails(selectedClusterId);
    }
  }, [selectedClusterId]);

  const loadClusterDetails = async (clusterId: string) => {
    try {
      const card = await api.getClusterDetails(clusterId);
      setClusterCard(card);
      setGoldenDesc(card.proposed_golden_record || "");
      setSelectedMaterialIds(card.materials.map((m: any) => m.material.id));
      setActionMessage(null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAction = async (decisionType: string) => {
    if (!selectedClusterId) return;
    setActionLoading(true);
    try {
      const res = await api.executeReviewAction({
        cluster_group_id: selectedClusterId,
        decision_type: decisionType,
        custom_golden_description: goldenDesc,
        selected_material_ids: selectedMaterialIds,
        reviewer_notes: reviewerNotes,
      });

      if (decisionType === "IDENTICAL" || decisionType === "SUBSTITUTE") {
        setActionMessage(`Successfully minted ${res.minted_cnmc} and registered in National Crosswalk.`);
      } else {
        setActionMessage(`Cluster marked as ${decisionType}`);
      }

      await loadQueue();
    } catch (err: any) {
      alert(`Action notice: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const toggleMaterialSelect = (matId: number) => {
    setSelectedMaterialIds((prev) =>
      prev.includes(matId) ? prev.filter((id) => id !== matId) : [...prev, matId]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between glass-card p-6 rounded-2xl">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2.5">
            <GitMerge className="h-5 w-5 text-zinc-300" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Governance Review Queue
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-normal">
            Side-by-side 3-way multi-CPSE cluster validation. Verify safety invariants, inspect score math, and mint Golden Records.
          </p>
        </div>

        <button
          onClick={loadQueue}
          className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Cluster List */}
        <div className="glass-card rounded-2xl p-4 space-y-3 h-[740px] overflow-y-auto">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
              Pending Clusters ({queueItems.length})
            </span>
          </div>

          {queueItems.length === 0 ? (
            <div className="text-center py-16 text-zinc-500 text-xs">
              All material clusters harmonized.
            </div>
          ) : (
            queueItems.map((q) => {
              const isSelected = q.cluster_group_id === selectedClusterId;
              return (
                <div
                  key={q.cluster_group_id}
                  onClick={() => setSelectedClusterId(q.cluster_group_id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all duration-150 apple-press-subtle ${
                    isSelected
                      ? "bg-zinc-800 border-white/20 shadow-sm ring-1 ring-white/10"
                      : "bg-zinc-900/60 border-white/[0.04] hover:bg-zinc-800/50 hover:border-white/[0.08]"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-white font-mono">
                      #{q.cluster_group_id.slice(0, 10)}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      q.confidence_tier === "HIGH"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      {q.confidence_tier}
                    </span>
                  </div>

                  <div className="text-[11px] text-zinc-300 font-medium truncate">
                    Category: {q.category_code}
                  </div>

                  <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-white/[0.04] text-[10px]">
                    <span className="text-zinc-400 font-mono">Score: {(q.composite_score * 100).toFixed(1)}%</span>
                    {q.safety_veto ? (
                      <span className="text-rose-400 font-semibold flex items-center">
                        <ShieldAlert className="h-3 w-3 mr-0.5 text-rose-400" /> Veto Alert
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-medium flex items-center">
                        <ShieldCheck className="h-3 w-3 mr-0.5 text-emerald-400" /> Invariant Safe
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right 3 Columns: 3-Way Cluster Card Review Screen */}
        <div className="lg:col-span-3 space-y-4">
          {clusterCard ? (
            <div className="glass-card rounded-2xl overflow-hidden space-y-5 p-6">
              {/* Cluster Card Top Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.08]">
                <div>
                  <div className="flex items-center space-x-2.5">
                    <span className="text-sm font-bold text-white font-mono">
                      Cluster #{clusterCard.cluster_group_id}
                    </span>
                    <span className="text-xs px-2.5 py-0.5 bg-zinc-800 text-zinc-300 rounded-full border border-white/[0.08] font-medium">
                      Category: {clusterCard.category_code}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {clusterCard.category_name}
                  </p>
                </div>

                <div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    clusterCard.confidence_tier === "HIGH"
                      ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                  }`}>
                    Match Confidence: {(clusterCard.composite_score * 100).toFixed(1)}% ({clusterCard.confidence_tier})
                  </span>
                </div>
              </div>

              {actionMessage && (
                <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-xl font-medium flex items-center space-x-2">
                  <Check className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                  <span>{actionMessage}</span>
                </div>
              )}

              {/* Multi-CPSE Candidate Cards (CPCL, IOCL, BPCL) */}
              <div className="space-y-3">
                <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
                  Multi-CPSE Match Candidates (Select items to include in merge):
                </span>

                <div className="space-y-3">
                  {clusterCard.materials.map((mItem: any) => {
                    const m = mItem.material;
                    const isSelected = selectedMaterialIds.includes(m.id);

                    return (
                      <div
                        key={m.id}
                        onClick={() => toggleMaterialSelect(m.id)}
                        className={`p-4 rounded-2xl border cursor-pointer transition-all duration-150 apple-press-subtle ${
                          isSelected
                            ? "bg-zinc-900 border-white/20 shadow-sm ring-1 ring-white/10"
                            : "bg-zinc-950/60 border-white/[0.04] opacity-50"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2.5">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleMaterialSelect(m.id)}
                              className="h-4 w-4 rounded bg-zinc-900 border-zinc-700 text-white focus:ring-0 cursor-pointer"
                            />
                            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-800 text-zinc-200 border border-white/[0.08]">
                              {m.cpse_code} SAP
                            </span>
                            <span className="font-mono text-xs font-bold text-white">
                              Code: {m.material_code}
                            </span>
                          </div>

                          <div className="flex items-center space-x-3 text-xs text-zinc-300">
                            <span>UOM: <strong className="text-white font-mono">{m.uom}</strong></span>
                            <span>Last PO: <strong className="text-emerald-400 font-mono">₹{mItem.last_po_price?.toLocaleString() || "N/A"}</strong></span>
                            <span>Vendor: <strong className="text-zinc-200">{mItem.vendor_name || "Unknown"}</strong></span>
                          </div>
                        </div>

                        {/* Raw Description */}
                        <div className="bg-zinc-950 p-3 rounded-xl border border-white/[0.04] mb-2.5">
                          <span className="text-[10px] uppercase font-semibold text-zinc-500 block mb-0.5">Source Specification:</span>
                          <span className="font-mono text-xs text-zinc-100 font-medium">{m.short_description}</span>
                        </div>

                        {/* Extracted Parametric Badges */}
                        <div className="flex flex-wrap gap-1.5 text-[11px]">
                          {m.item_noun && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              {m.item_noun}
                            </span>
                          )}
                          {m.nominal_size && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              Size: {m.nominal_size}
                            </span>
                          )}
                          {m.pressure_class && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              Rating: {m.pressure_class}
                            </span>
                          )}
                          {m.schedule && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              Schedule: {m.schedule}
                            </span>
                          )}
                          {m.moc && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              MOC: {m.moc}
                            </span>
                          )}
                          {m.end_connection && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06]">
                              End: {m.end_connection}
                            </span>
                          )}
                          {m.clean_part_number && (
                            <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-200 rounded-md border border-white/[0.06] font-mono">
                              Part: {m.clean_part_number}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Explainable Match Score Breakdown */}
              <div className="p-4 rounded-2xl bg-zinc-950 border border-white/[0.08] space-y-2.5">
                <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
                  Explainable Zero-Training Score Breakdown:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 bg-zinc-900/60 rounded-xl border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">Semantic Embedding (40%)</span>
                    <span className="font-bold text-white font-mono">
                      {(clusterCard.scores.semantic_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2.5 bg-zinc-900/60 rounded-xl border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">Parametric Spec (35%)</span>
                    <span className="font-bold text-white font-mono">
                      {(clusterCard.scores.attribute_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2.5 bg-zinc-900/60 rounded-xl border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">Procurement Graph (25%)</span>
                    <span className="font-bold text-white font-mono">
                      {(clusterCard.scores.procurement_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2.5 bg-zinc-900/60 rounded-xl border border-white/[0.04]">
                    <span className="text-zinc-400 block text-[10px]">Safety Guardrail</span>
                    {clusterCard.scores.safety_veto ? (
                      <span className="font-bold text-rose-400 flex items-center text-[11px]">
                        <ShieldAlert className="h-3.5 w-3.5 mr-1 text-rose-400" /> VETOED ({clusterCard.scores.veto_reason})
                      </span>
                    ) : (
                      <span className="font-bold text-emerald-400 flex items-center text-[11px]">
                        <ShieldCheck className="h-3.5 w-3.5 mr-1 text-emerald-400" /> PASSED
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Proposed ISO 8000 Golden Record Box */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider block">
                  Proposed Golden Record (ISO 8000 Noun-Modifier Format):
                </span>
                <textarea
                  value={goldenDesc}
                  onChange={(e) => setGoldenDesc(e.target.value)}
                  rows={2}
                  className="w-full glass-input rounded-xl p-3.5 text-xs font-mono text-emerald-300 focus:outline-none font-semibold"
                />
              </div>

              {/* Reviewer Notes */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-zinc-400">Reviewer Governance Notes:</label>
                <input
                  type="text"
                  placeholder="e.g. Verified ASME B16.34 specifications & L&T supply history. Approved."
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  className="w-full glass-input rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-3 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08]">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleAction("REJECT")}
                    disabled={actionLoading}
                    className="flex items-center space-x-1.5 px-3.5 py-2 bg-rose-950/30 hover:bg-rose-900/50 text-rose-300 border border-rose-800/40 rounded-xl text-xs font-medium apple-press transition disabled:opacity-50"
                  >
                    <XCircle className="h-3.5 w-3.5 text-rose-400" />
                    <span>Reject Match</span>
                  </button>
                  <button
                    onClick={() => handleAction("SPLIT")}
                    disabled={actionLoading}
                    className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition disabled:opacity-50"
                  >
                    <Split className="h-3.5 w-3.5" />
                    <span>Split Cluster</span>
                  </button>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => handleAction("SUBSTITUTE")}
                    disabled={actionLoading}
                    className="flex items-center space-x-1.5 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-xl text-xs font-semibold apple-press transition disabled:opacity-50"
                  >
                    <GitMerge className="h-3.5 w-3.5" />
                    <span>Approve as Substitute</span>
                  </button>

                  <button
                    onClick={() => handleAction("IDENTICAL")}
                    disabled={actionLoading}
                    className="flex items-center space-x-2 px-5 py-2 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press transition disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4 text-black" />
                    <span>Approve and Mint CNMC</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card rounded-2xl p-16 text-center text-zinc-500 text-xs">
              Select a cluster from the left queue to inspect and take action.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
