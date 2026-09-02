"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Database, Search, RefreshCw } from "lucide-react";

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [cpseFilter, setCpseFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const loadMaterials = async () => {
    setLoading(true);
    try {
      const data = await api.getMaterials({
        cpse_code: cpseFilter || undefined,
        search: search || undefined,
        limit: 100,
      });
      setMaterials(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, [cpseFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadMaterials();
  };

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
            Browse raw and standardized items across CPCL, IOCL, and BPCL refinery datasets.
          </p>
        </div>

        <button
          onClick={loadMaterials}
          className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Catalog</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 rounded-2xl">
        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <input
              type="text"
              placeholder="Search by code, keyword, part no, or noun (e.g. valve, pipe, 6205)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-4 py-2.5 text-xs focus:outline-none"
            />
          </div>

          <div>
            <select
              value={cpseFilter}
              onChange={(e) => setCpseFilter(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
            >
              <option value="">All Refineries</option>
              <option value="CPCL">CPCL</option>
              <option value="IOCL">IOCL</option>
              <option value="BPCL">BPCL</option>
            </select>
          </div>

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
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">Refinery</th>
                <th className="py-3.5 px-4">Local Code</th>
                <th className="py-3.5 px-4">Source Specification</th>
                <th className="py-3.5 px-4">Deterministic Extracted Specs</th>
                <th className="py-3.5 px-4">UOM</th>
                <th className="py-3.5 px-4 text-right">Last PO Price</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono">
              {materials.map((m) => {
                return (
                  <tr key={m.id} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-800 text-zinc-200 border border-white/[0.08]">
                        {m.cpse_code}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white">{m.material_code}</td>
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
                        {m.package_multiplier > 1.0 && (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] font-semibold border border-white/[0.06]">
                            {m.package_multiplier}x
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-zinc-300 font-sans">{m.uom}</td>
                    <td className="py-3.5 px-4 text-right font-bold text-emerald-400 font-mono">
                      ₹{m.last_po_price?.toLocaleString() || "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
