"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { 
  GitMerge, 
  CheckCircle2, 
  XCircle, 
  Split, 
  ShieldCheck, 
  ShieldAlert, 
  Check, 
  RefreshCw, 
  Sparkles, 
  ChevronRight, 
  Info, 
  Search, 
  X 
} from "lucide-react";

export default function ReviewQueuePage() {
  const [statusFilter, setStatusFilter] = useState<string>("PENDING");
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [filterQuery, setFilterQuery] = useState("");
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [clusterCard, setClusterCard] = useState<any>(null);
  const [goldenDesc, setGoldenDesc] = useState<string>("");
  const [reviewerNotes, setReviewerNotes] = useState<string>("");
  const [selectedRelationship, setSelectedRelationship] = useState<string>("IDENTICAL");
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<number[]>([]);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [showScoreDetail, setShowScoreDetail] = useState(false);
  
  const [page, setPage] = useState<number>(0);
  const pageSize = 25;
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  
  // Dispute Modal State
  const [disputeModalOpen, setDisputeModalOpen] = useState(false);
  const [disputeReason, setDisputeReason] = useState("");
  const [disputeCpse, setDisputeCpse] = useState("IOCL");

  // Real-time filtering across cluster ID, category, and item noun
  const filteredQueueItems = useMemo(() => {
    if (!filterQuery.trim()) return queueItems;
    const qLower = filterQuery.toLowerCase().trim();
    return queueItems.filter((q: any) =>
      (q.cluster_group_id || "").toLowerCase().includes(qLower) ||
      (q.category_code || "").toLowerCase().includes(qLower) ||
      (q.category_name || "").toLowerCase().includes(qLower)
    );
  }, [queueItems, filterQuery]);

  // Governance Safety: Synchronize selectedClusterId so active review pane always aligns with visible filter
  useEffect(() => {
    if (filteredQueueItems.length > 0) {
      const isCurrentInFiltered = filteredQueueItems.some(
        (i: any) => i.cluster_group_id === selectedClusterId
      );
      if (!isCurrentInFiltered) {
        setSelectedClusterId(filteredQueueItems[0].cluster_group_id);
      }
    } else {
      setSelectedClusterId(null);
      setClusterCard(null);
    }
  }, [filteredQueueItems, selectedClusterId]);

  const loadQueue = async (targetPage = page) => {
    setLoading(true);
    try {
      const items = await api.getReviewQueue({
        statusFilter,
        limit: pageSize,
        offset: targetPage * pageSize,
      });
      setQueueItems(items || []);
      if (items && items.length > 0 && (!selectedClusterId || !items.some((i: any) => i.cluster_group_id === selectedClusterId))) {
        setSelectedClusterId(items[0].cluster_group_id);
      } else if (!items || items.length === 0) {
        setSelectedClusterId(null);
        setClusterCard(null);
      }
    } catch (err) {
      console.error("Queue load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(0);
    loadQueue(0);
  }, [statusFilter]);

  useEffect(() => {
    if (selectedClusterId) {
      loadClusterDetails(selectedClusterId);
    }
  }, [selectedClusterId]);

  const loadClusterDetails = async (clusterId: string) => {
    try {
      const card = await api.getClusterDetails(clusterId);
      setClusterCard(card);
      setGoldenDesc(card?.proposed_golden_record || "");
      setSelectedMaterialIds((card?.materials || []).map((m: any) => m.material.id));
      setActionMessage(null);
      
      // Smart default relationship based on confidence
      if (card?.composite_score >= 0.95) {
        setSelectedRelationship("IDENTICAL");
      } else {
        setSelectedRelationship("FUNCTIONAL_EQUIVALENT");
      }
    } catch (err) {
      console.error("Cluster detail load error:", err);
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
        reviewer_notes: reviewerNotes || "Validated via Apple-Standard Human-In-The-Loop Review",
      });

      if (res?.minted_cnmc) {
        setActionMessage(`Approved! Minted ${res.minted_cnmc} and indexed in National Master Directory.`);
      } else {
        setActionMessage(`Cluster marked as ${decisionType}.`);
      }

      await loadQueue();
    } catch (err: any) {
      alert(`Action error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const toggleMaterialSelect = (matId: number) => {
    setSelectedMaterialIds((prev) =>
      prev.includes(matId) ? prev.filter((id) => id !== matId) : [...prev, matId]
    );
  };

  const handleBulkApprove = async () => {
    const highConfIds = queueItems
      .filter((q) => q.confidence_tier === "HIGH" && !q.safety_veto)
      .map((q) => q.cluster_group_id);
    if (highConfIds.length === 0) return;

    setActionLoading(true);
    try {
      const res = await api.bulkApprove(highConfIds);
      setActionMessage(`Approved ${res.approved_count} high-confidence clusters.`);
      await loadQueue();
    } catch (err: any) {
      alert(`Bulk approval error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const highConfidenceCount = queueItems.filter(q => q.confidence_tier === "HIGH" && !q.safety_veto).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Executive Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <GitMerge className="h-5 w-5 text-zinc-900 dark:text-zinc-100" />
            <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              Governance Review Queue
            </h1>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-2xl leading-relaxed">
            Validate multi-enterprise match candidates. Compare attributes side-by-side, verify safety invariants, and mint National CNMC Golden Records.
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex items-center space-x-2.5">
          {highConfidenceCount > 0 && statusFilter === "PENDING" && (
            <button
              onClick={handleBulkApprove}
              disabled={actionLoading}
              className="flex items-center space-x-1.5 h-8.5 px-3.5 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-950 rounded-xl text-xs font-semibold apple-press transition shadow-sm"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 dark:text-emerald-600" />
              <span>Approve All ({highConfidenceCount}) High-Confidence</span>
            </button>
          )}

          <button
            onClick={() => loadQueue()}
            className="flex items-center space-x-1.5 h-8.5 px-3 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs font-medium apple-press transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Review Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 4 Cols: Queue List */}
        <div className="lg:col-span-4 glass-card rounded-2xl p-4 space-y-3 max-h-[820px] overflow-y-auto">
          {/* Segmented Status Pill */}
          <div className="grid grid-cols-4 gap-1 p-0.5 bg-zinc-100 dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-medium">
            {(["PENDING", "APPROVED", "DISPUTED", "REJECTED"] as const).map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`py-1.5 rounded-lg transition text-center text-[11px] ${
                  statusFilter === st
                    ? "bg-white dark:bg-zinc-800 text-zinc-950 dark:text-white shadow-sm font-semibold"
                    : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
                }`}
              >
                {st === "PENDING" ? "Pending" : st.charAt(0) + st.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          <div className="text-[11px] text-zinc-500 font-mono px-1 flex items-center justify-between">
            <span>{filteredQueueItems.length} items in view</span>
            <span>Page {page + 1}</span>
          </div>

          {/* Quick Filter Input */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-zinc-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filter by noun, cluster ID..."
              className="w-full h-8 pl-8 pr-7 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:border-zinc-400"
            />
            {filterQuery && (
              <button
                onClick={() => setFilterQuery("")}
                className="absolute right-2 top-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* List Items */}
          <div className="space-y-2">
            {filteredQueueItems.map((q) => {
              const isSelected = q.cluster_group_id === selectedClusterId;
              return (
                <div
                  key={q.cluster_group_id}
                  onClick={() => setSelectedClusterId(q.cluster_group_id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all apple-press-subtle ${
                    isSelected
                      ? "bg-zinc-100/90 dark:bg-zinc-800/90 border-zinc-300 dark:border-zinc-600 shadow-sm"
                      : "bg-white/70 dark:bg-zinc-950/60 border-zinc-200/80 dark:border-zinc-800/80 hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-mono font-bold text-zinc-900 dark:text-zinc-100">
                      #{q.cluster_group_id}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-zinc-200/60 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300">
                      {(q.composite_score * 100).toFixed(0)}% Match
                    </span>
                  </div>

                  <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate">
                    {q.category_code} · {q.category_name || "General Catalog"}
                  </p>

                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 text-[10px]">
                    {q.safety_veto ? (
                      <span className="text-red-600 dark:text-red-400 font-medium flex items-center">
                        <ShieldAlert className="h-3 w-3 mr-1" /> Veto Alert
                      </span>
                    ) : (
                      <span className="text-emerald-700 dark:text-emerald-400 font-medium flex items-center">
                        <ShieldCheck className="h-3 w-3 mr-1" /> Safe Match
                      </span>
                    )}
                    <ChevronRight className="h-3 w-3 text-zinc-400" />
                  </div>
                </div>
              );
            })}

            {filteredQueueItems.length === 0 && (
              <div className="text-center py-12 text-zinc-400 text-xs font-sans space-y-1">
                <p className="font-medium">No matching clusters found.</p>
                <p className="text-[11px] text-zinc-500">
                  {filterQuery ? `No candidates match "${filterQuery}".` : "Queue is currently empty for this status."}
                </p>
              </div>
            )}
          </div>

          {/* Pagination */}
          {queueItems.length > 0 && (
            <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500">
              <button
                onClick={() => { if (page > 0) { setPage(page - 1); loadQueue(page - 1); } }}
                disabled={page === 0}
                className="h-7 px-2.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 disabled:opacity-30 border border-zinc-200 dark:border-zinc-800 transition"
              >
                Previous
              </button>
              <button
                onClick={() => { if (queueItems.length === pageSize) { setPage(page + 1); loadQueue(page + 1); } }}
                disabled={queueItems.length < pageSize}
                className="h-7 px-2.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 disabled:opacity-30 border border-zinc-200 dark:border-zinc-800 transition"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Right 8 Cols: Side-by-Side Comparison Workspace */}
        <div className="lg:col-span-8 space-y-4">
          {clusterCard ? (
            <div className="glass-card rounded-2xl p-6 space-y-6">
              {/* Card Header & Confidence Glance */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-zinc-200 dark:border-zinc-800">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-semibold font-mono text-zinc-900 dark:text-zinc-100">
                      Cluster #{clusterCard.cluster_group_id}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded font-mono">
                      {clusterCard.category_code}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    Comparing {clusterCard.materials?.length || 0} candidate items across enterprises
                  </p>
                </div>

                {/* Glanceable Match Score Pill */}
                <div className="flex items-center space-x-2">
                  <div 
                    onClick={() => setShowScoreDetail(!showScoreDetail)}
                    className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 cursor-pointer hover:border-zinc-300 dark:hover:border-zinc-700 transition"
                  >
                    {clusterCard.scores?.safety_veto ? (
                      <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
                    ) : (
                      <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                    <span className="text-xs font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                      {(clusterCard.composite_score * 100).toFixed(1)}% Match
                    </span>
                    <Info className="h-3 w-3 text-zinc-400" />
                  </div>
                </div>
              </div>

              {/* Action Message Feedback */}
              {actionMessage && (
                <div className="p-3.5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-200 text-xs rounded-xl flex items-center space-x-2">
                  <Check className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <span>{actionMessage}</span>
                </div>
              )}

              {/* Explainable Score Drilldown (Progressive Disclosure) */}
              {showScoreDetail && (
                <div className="p-4 bg-zinc-50 dark:bg-zinc-950/70 rounded-xl border border-zinc-200 dark:border-zinc-800 space-y-2 text-xs">
                  <span className="font-semibold text-zinc-800 dark:text-zinc-200 block text-[11px] uppercase tracking-wider">
                    Score Weight Breakdown:
                  </span>
                  <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                    <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
                      <span className="text-zinc-500 block text-[10px]">Semantic Text (40%)</span>
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">{((clusterCard.scores?.semantic_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
                      <span className="text-zinc-500 block text-[10px]">Parametric Spec (35%)</span>
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">{((clusterCard.scores?.attribute_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
                      <span className="text-zinc-500 block text-[10px]">Procurement Graph (25%)</span>
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">{((clusterCard.scores?.procurement_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Side-by-Side Attribute Comparison Grid */}
              <div className="space-y-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-mono block">
                  Candidate Specifications Side-by-Side:
                </span>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(clusterCard.materials || []).map((mItem: any) => {
                    const m = mItem.material;
                    const isChecked = selectedMaterialIds.includes(m.id);

                    return (
                      <div
                        key={m.id}
                        onClick={() => toggleMaterialSelect(m.id)}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-3 ${
                          isChecked 
                            ? "bg-zinc-50/90 dark:bg-zinc-900/90 border-zinc-300 dark:border-zinc-700 shadow-sm" 
                            : "bg-white/60 dark:bg-zinc-950/60 border-zinc-200/80 dark:border-zinc-800/80 opacity-50"
                        }`}
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 dark:border-zinc-800/60">
                          <div className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => toggleMaterialSelect(m.id)}
                              className="h-3.5 w-3.5 rounded"
                            />
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-zinc-200 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 font-mono">
                              {m.cpse_code}
                            </span>
                          </div>
                          <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                            {m.material_code}
                          </span>
                        </div>

                        {/* Raw Description */}
                        <p className="text-xs text-zinc-700 dark:text-zinc-300 font-sans leading-relaxed line-clamp-2" title={m.short_description}>
                          {m.short_description}
                        </p>

                        {/* Extracted Attribute Pills */}
                        <div className="space-y-1.5 text-[11px] font-mono">
                          <div className="flex justify-between py-1 border-b border-zinc-200/40 dark:border-zinc-800/40">
                            <span className="text-zinc-500">Noun:</span>
                            <span className="font-medium text-zinc-900 dark:text-zinc-100">{m.item_noun || "—"}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-zinc-200/40 dark:border-zinc-800/40">
                            <span className="text-zinc-500">Size:</span>
                            <span className="font-medium text-zinc-900 dark:text-zinc-100">{m.nominal_size || "—"}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-zinc-200/40 dark:border-zinc-800/40">
                            <span className="text-zinc-500">Rating:</span>
                            <span className="font-medium text-zinc-900 dark:text-zinc-100">{m.pressure_class || "—"}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-zinc-200/40 dark:border-zinc-800/40">
                            <span className="text-zinc-500">MOC:</span>
                            <span className="font-medium text-zinc-900 dark:text-zinc-100">{m.moc || "—"}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-zinc-200/40 dark:border-zinc-800/40">
                            <span className="text-zinc-500">End Conn:</span>
                            <span className="font-medium text-zinc-900 dark:text-zinc-100">{m.end_connection || "—"}</span>
                          </div>
                          <div className="flex justify-between py-1">
                            <span className="text-zinc-500">Last PO:</span>
                            <span className="font-bold text-zinc-900 dark:text-zinc-100 tabular-nums">
                              ₹{mItem.last_po_price ? mItem.last_po_price.toLocaleString() : "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Proposed ISO 8000 Golden Record */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-mono block">
                  Standardized ISO 8000 Description (Noun-Modifier Format):
                </span>
                <textarea
                  value={goldenDesc}
                  onChange={(e) => setGoldenDesc(e.target.value)}
                  rows={2}
                  className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 text-xs font-mono font-medium text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600"
                />
              </div>

              {/* Primary Action Buttons Bar */}
              <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleAction("SPLIT")}
                    disabled={actionLoading}
                    className="h-9 px-3.5 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs font-medium apple-press transition flex items-center space-x-1.5"
                  >
                    <Split className="h-3.5 w-3.5" />
                    <span>Split Cluster</span>
                  </button>

                  <button
                    onClick={() => setDisputeModalOpen(true)}
                    disabled={actionLoading}
                    className="h-9 px-3.5 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs font-medium apple-press transition flex items-center space-x-1.5"
                  >
                    <ShieldAlert className="h-3.5 w-3.5 text-zinc-500" />
                    <span>Flag Dispute</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                    className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 px-2 py-1"
                  >
                    {showAdvancedOptions ? "Simple" : "More Options..."}
                  </button>
                </div>

                <div className="flex items-center space-x-2">
                  {showAdvancedOptions && (
                    <select
                      value={selectedRelationship}
                      onChange={(e) => setSelectedRelationship(e.target.value)}
                      className="h-9 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-xl px-2.5 text-xs font-medium focus:outline-none"
                    >
                      <option value="IDENTICAL">Identical (100% Equivalent)</option>
                      <option value="FUNCTIONAL_EQUIVALENT">Functional Equivalent</option>
                      <option value="BRAND_ALTERNATIVE">Brand Alternative</option>
                      <option value="KIT_COMPONENT">Kit Component</option>
                      <option value="PACKAGING_VARIANT">Packaging Variant</option>
                      <option value="SUPERSEDED">Superseded / Upgraded</option>
                    </select>
                  )}

                  <button
                    onClick={() => handleAction(selectedRelationship)}
                    disabled={actionLoading || selectedMaterialIds.length === 0}
                    className="h-9 px-5 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-950 rounded-xl text-xs font-semibold apple-press transition shadow-sm flex items-center space-x-2 disabled:opacity-40"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Approve & Mint CNMC</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card rounded-2xl p-20 text-center text-zinc-400 text-xs font-sans">
              Select a cluster from the left queue to compare and validate.
            </div>
          )}
        </div>
      </div>

      {/* In-App Multi-CPSE Dispute Arbitration Modal */}
      {disputeModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-lg w-full rounded-2xl p-6 space-y-4 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-2xl">
            <div className="flex items-center space-x-2.5 border-b border-zinc-200 dark:border-zinc-800 pb-3">
              <ShieldAlert className="h-4 w-4 text-amber-500" />
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">File Formal CPSE Arbitration Dispute</h3>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Escalates this match candidate to the National Data Steward.</p>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-zinc-700 dark:text-zinc-300 font-medium block mb-1">Dissenting CPSE Entity</label>
                <select
                  value={disputeCpse}
                  onChange={(e) => setDisputeCpse(e.target.value)}
                  className="w-full h-8.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 rounded-xl px-2.5 focus:outline-none"
                >
                  <option value="IOCL">IOCL (Indian Oil)</option>
                  <option value="CPCL">CPCL (Chennai Petroleum)</option>
                  <option value="BPCL">BPCL (Bharat Petroleum)</option>
                  <option value="ONGC">ONGC</option>
                  <option value="NTPC">NTPC</option>
                  <option value="SAIL">SAIL</option>
                  <option value="BHEL">BHEL</option>
                  <option value="COALINDIA">Coal India</option>
                </select>
              </div>

              <div>
                <label className="text-zinc-700 dark:text-zinc-300 font-medium block mb-1">Technical Ground for Dispute</label>
                <textarea
                  rows={3}
                  placeholder="Explain why materials are not interchangeable (e.g. pressure rating mismatch, metallurgy difference)..."
                  value={disputeReason}
                  onChange={(e) => setDisputeReason(e.target.value)}
                  className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 rounded-xl p-3 focus:outline-none font-sans"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setDisputeModalOpen(false)}
                className="h-8.5 px-3 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 rounded-xl text-xs font-medium apple-press transition"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!selectedClusterId || !disputeReason.trim()) return;
                  setActionLoading(true);
                  try {
                    await api.fileDispute(selectedClusterId, disputeReason.trim(), disputeCpse);
                    setDisputeModalOpen(false);
                    setDisputeReason("");
                    setActionMessage(`Dispute filed by ${disputeCpse}. Escalated to National Data Steward.`);
                    await loadQueue();
                  } catch (e: any) {
                    alert(`Dispute filing error: ${e.message}`);
                  } finally {
                    setActionLoading(false);
                  }
                }}
                disabled={!disputeReason.trim() || actionLoading}
                className="h-8.5 px-4 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-950 rounded-xl text-xs font-semibold apple-press transition disabled:opacity-50"
              >
                Submit Dispute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
