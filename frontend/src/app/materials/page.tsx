"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Database, Search, RefreshCw, X, Layers, Award, Tag } from "lucide-react";

export default function MaterialsPage() {
  const [activeTab, setActiveTab] = useState<"LOCAL" | "GOLDEN">("LOCAL");
  const [materials, setMaterials] = useState<any[]>([]);
  const [goldenRecords, setGoldenRecords] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [cpseFilter, setCpseFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedMaterial, setSelectedMaterial] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadMaterials = async () => {
    setLoading(true);
    try {
      if (activeTab === "LOCAL") {
        const data = await api.getMaterials({
          cpse_code: cpseFilter || undefined,
          search: search || undefined,
          limit: 100,
        });
        setMaterials(data);
      } else {
        const registry = await api.getCrosswalkRegistry();
        setGoldenRecords(registry);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, [cpseFilter, activeTab]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadMaterials();
  };

  const handleRowClick = async (matId: number) => {
    setDetailLoading(true);
    try {
      const detail = await api.getMaterialDetail(matId);
      setSelectedMaterial(detail);
    } catch (err) {
      console.error("Failed to load material detail", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const filteredGolden = goldenRecords.filter((g) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const cnmc = (g.cnmc_code || "").toLowerCase();
    const desc = (g.golden_record?.standardized_description || "").toLowerCase();
    return cnmc.includes(q) || desc.includes(q);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2.5">
            <Database className="h-5 w-5 text-zinc-300" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Master Materials Catalog
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-normal">
            Browse raw CPSE catalog records and authoritative National Golden Records (CNMC).
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Tab Switcher */}
          <div className="flex items-center bg-zinc-900 border border-white/[0.08] p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("LOCAL")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "LOCAL" ? "bg-white text-black shadow" : "text-zinc-400 hover:text-white"
              }`}
            >
              CPSE Local Records
            </button>
            <button
              onClick={() => setActiveTab("GOLDEN")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1 ${
                activeTab === "GOLDEN" ? "bg-emerald-500 text-black shadow" : "text-zinc-400 hover:text-white"
              }`}
            >
              <Award className="h-3.5 w-3.5" />
              <span>National Golden (CNMC)</span>
            </button>
          </div>

          <button
            onClick={loadMaterials}
            className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 rounded-2xl">
        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className={activeTab === "LOCAL" ? "sm:col-span-2" : "sm:col-span-3"}>
            <input
              type="text"
              placeholder={activeTab === "LOCAL" ? "Search by code, keyword, part no, or noun (e.g. valve, pipe, 6205)..." : "Search CNMC Code or Golden Description..."}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-4 py-2.5 text-xs focus:outline-none"
            />
          </div>

          {activeTab === "LOCAL" && (
            <div>
              <select
                value={cpseFilter}
                onChange={(e) => setCpseFilter(e.target.value)}
                className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
              >
                <option value="">All CPSEs (8 National)</option>
                <option value="CPCL">CPCL (Chennai Petroleum)</option>
                <option value="IOCL">IOCL (Indian Oil)</option>
                <option value="BPCL">BPCL (Bharat Petroleum)</option>
                <option value="NTPC">NTPC Limited</option>
                <option value="SAIL">SAIL (Steel Authority)</option>
                <option value="ONGC">ONGC</option>
                <option value="COALINDIA">Coal India</option>
                <option value="BHEL">BHEL</option>
              </select>
            </div>
          )}

          <div>
            <button
              type="submit"
              className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press transition"
            >
              <Search className="h-3.5 w-3.5 text-black" />
              <span>Search Catalog</span>
            </button>
          </div>
        </form>
      </div>

      {/* Table */}
      <div className="glass-card rounded-2xl overflow-hidden shadow-sm">
        {activeTab === "LOCAL" ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-300">
              <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                <tr>
                  <th className="py-3.5 px-4">CPSE</th>
                  <th className="py-3.5 px-4">Local Code</th>
                  <th className="py-3.5 px-4">Source Specification</th>
                  <th className="py-3.5 px-4">Extracted Specs</th>
                  <th className="py-3.5 px-4">UOM</th>
                  <th className="py-3.5 px-4 text-right">Last PO Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono">
                {materials.map((m) => (
                  <tr
                    key={m.id}
                    onClick={() => handleRowClick(m.id)}
                    className="hover:bg-zinc-900/60 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-800 text-zinc-200 border border-white/[0.08]">
                        {m.cpse_code}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white hover:text-emerald-400 underline decoration-zinc-600 underline-offset-4">
                      {m.material_code}
                    </td>
                    <td className="py-3.5 px-4 text-zinc-300 text-[11px] font-sans font-medium">{m.short_description}</td>
                    <td className="py-3.5 px-4 font-sans">
                      <div className="flex flex-wrap gap-1">
                        {m.item_noun && (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                            {m.item_noun}
                          </span>
                        )}
                        {m.nominal_size && (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                            {m.nominal_size}
                          </span>
                        )}
                        {m.pressure_class && (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                            {m.pressure_class}
                          </span>
                        )}
                        {m.moc && (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                            {m.moc}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-zinc-300 font-sans">{m.uom}</td>
                    <td className="py-3.5 px-4 text-right font-bold text-emerald-400 font-mono">
                      ₹{m.last_po_price?.toLocaleString() || "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-300">
              <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                <tr>
                  <th className="py-3.5 px-4">Authoritative CNMC Code</th>
                  <th className="py-3.5 px-4">Standardized Description (ISO 8000)</th>
                  <th className="py-3.5 px-4">Base UOM</th>
                  <th className="py-3.5 px-4">Linked CPSE Items</th>
                  <th className="py-3.5 px-4 text-right">Governed Price Range</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredGolden.map((g, idx) => (
                  <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                      {g.cnmc_code}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-white text-[12px]">
                      {g.golden_record?.standardized_description}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-zinc-300">
                      {g.golden_record?.base_uom || "EA"}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {g.crosswalk_links?.map((link: any, lIdx: number) => (
                          <span
                            key={lIdx}
                            className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-white/[0.06]"
                            title={`${link.cpse_code}: ${link.short_description}`}
                          >
                            {link.cpse_code}: {link.local_material_code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-zinc-200">
                      ₹{g.crosswalk_links?.[0]?.last_po_price?.toLocaleString() || "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Material Detail Slideover / Modal */}
      {selectedMaterial && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-2xl w-full rounded-2xl p-6 space-y-5 border border-white/[0.1] bg-zinc-950/95 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-zinc-800 text-zinc-200">
                    {selectedMaterial.cpse_code}
                  </span>
                  <h3 className="text-base font-mono font-bold text-white">
                    {selectedMaterial.material_code}
                  </h3>
                </div>
                <p className="text-xs text-zinc-400 mt-1">
                  {selectedMaterial.short_description}
                </p>
              </div>
              <button
                onClick={() => setSelectedMaterial(null)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Deterministic Specs */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                Deterministic Normalized Attributes
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">Item Noun</span>
                  <span className="font-semibold text-white">{selectedMaterial.item_noun || "—"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">Nominal Size</span>
                  <span className="font-semibold text-white">{selectedMaterial.nominal_size || "—"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">Pressure Class</span>
                  <span className="font-semibold text-white">{selectedMaterial.pressure_class || "—"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">Material of Construction</span>
                  <span className="font-semibold text-white">{selectedMaterial.moc || "—"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">End Connection</span>
                  <span className="font-semibold text-white">{selectedMaterial.end_connection || "—"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 block">Base UOM</span>
                  <span className="font-semibold text-white">{selectedMaterial.uom} (Base: {selectedMaterial.base_uom})</span>
                </div>
              </div>
            </div>

            {/* Extracted Attributes Raw JSON */}
            {selectedMaterial.extracted_attributes && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Complete Extracted Parameter Vector
                </h4>
                <pre className="p-3 bg-zinc-900/90 rounded-xl text-[11px] font-mono text-emerald-400 overflow-x-auto border border-white/[0.05]">
                  {JSON.stringify(selectedMaterial.extracted_attributes, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedMaterial(null)}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-xs font-bold transition"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
