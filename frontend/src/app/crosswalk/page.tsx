"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { 
  Layers, 
  Search, 
  Download, 
  CheckCircle2
} from "lucide-react";

export default function CrosswalkPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCPSE, setSelectedCPSE] = useState("");
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const res = await api.reverseLookup(searchQuery.trim(), selectedCPSE || undefined);
      setLookupResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = (cpse?: string) => {
    const url = `http://localhost:8000/api/v1/export/sap-lsmw-csv${cpse ? `?cpse_code=${cpse}` : ""}`;
    window.open(url, "_blank");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2.5">
            <Layers className="h-5 w-5 text-zinc-300" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              National Crosswalk Registry
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-normal">
            Search any legacy CPCL, IOCL, or BPCL material code to resolve the National CNMC authority and its sister links.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleExportCSV()}
            className="flex items-center space-x-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-xl text-xs font-semibold apple-press transition"
          >
            <Download className="h-4 w-4" />
            <span>Export SAP LSMW CSV</span>
          </button>
        </div>
      </div>

      {/* Spotlight Search Box */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider block">
          Reverse Code Lookup & N:1 Crosswalk Resolver
        </span>

        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <input
              type="text"
              placeholder="Enter CPCL/IOCL/BPCL Code (e.g. 100234, 889102, 445511)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-4 py-2.5 text-xs font-mono focus:outline-none"
            />
          </div>

          <div>
            <select
              value={selectedCPSE}
              onChange={(e) => setSelectedCPSE(e.target.value)}
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
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press transition"
            >
              <Search className="h-3.5 w-3.5 text-black" />
              <span>{loading ? "Resolving..." : "Reverse Lookup"}</span>
            </button>
          </div>
        </form>

        {/* Quick Demo Chips */}
        <div className="flex items-center space-x-2 text-[11px] text-zinc-400 pt-1">
          <span>Quick Demo:</span>
          <button
            type="button"
            onClick={() => { setSearchQuery("100234"); setSelectedCPSE("CPCL"); }}
            className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg font-mono text-[10px] border border-white/[0.08] apple-press"
          >
            100234 (CPCL Gate Valve)
          </button>
          <button
            type="button"
            onClick={() => { setSearchQuery("889102"); setSelectedCPSE("IOCL"); }}
            className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg font-mono text-[10px] border border-white/[0.08] apple-press"
          >
            889102 (IOCL Gate Valve)
          </button>
          <button
            type="button"
            onClick={() => { setSearchQuery("100888"); setSelectedCPSE("CPCL"); }}
            className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-lg font-mono text-[10px] border border-white/[0.08] apple-press"
          >
            100888 (CPCL 4" Pipe)
          </button>
        </div>
      </div>

      {/* Lookup Details Card */}
      {lookupResult && lookupResult.found && lookupResult.cnmc_details && (
        <div className="glass-card rounded-2xl overflow-hidden shadow-sm space-y-4 p-6 border-white/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.08]">
            <div>
              <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-400 block mb-1">
                Resolved National Master Authority
              </span>
              <div className="flex items-center space-x-3">
                <span className="text-xl font-bold font-mono text-white bg-zinc-900 px-3.5 py-1 rounded-xl border border-white/[0.12]">
                  {lookupResult.cnmc_details.cnmc_code}
                </span>
                <span className="text-xs px-2.5 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 rounded-full font-medium flex items-center">
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Active National Code
                </span>
              </div>
            </div>

            <div className="text-right text-xs">
              <span className="text-zinc-500 block text-[11px]">Issued Authority Date:</span>
              <span className="font-mono text-zinc-200 font-bold">
                {new Date(lookupResult.cnmc_details.issued_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {/* ISO 8000 Golden Description */}
          <div className="p-4 rounded-xl bg-zinc-950 border border-white/[0.06]">
            <span className="text-[10px] uppercase font-semibold text-zinc-500 block mb-1">
              ISO 8000 Standardized Golden Description:
            </span>
            <span className="text-sm font-mono font-bold text-zinc-100">
              {lookupResult.cnmc_details.golden_record.standardized_description}
            </span>
          </div>

          {/* Mapped Sister CPSEs Crosswalk Table */}
          <div className="space-y-2">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
              Unified CPSE Crosswalk Mappings (N:1 Linkage):
            </span>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                  <tr>
                    <th className="py-3 px-4">Refinery Entity</th>
                    <th className="py-3 px-4">Local Code</th>
                    <th className="py-3 px-4">Local Description</th>
                    <th className="py-3 px-4">Mapping Type</th>
                    <th className="py-3 px-4 text-right">Last PO Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {lookupResult.cnmc_details.crosswalk_links.map((link: any, idx: number) => {
                    const isQueried = link.local_material_code === searchQuery.trim();

                    return (
                      <tr key={idx} className={isQueried ? "bg-zinc-900/90" : "hover:bg-zinc-900/40 transition-colors"}>
                        <td className="py-3.5 px-4 font-bold">
                          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-zinc-800 text-zinc-200 border border-white/[0.08]">
                            {link.cpse_code}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-white">
                          {link.local_material_code}
                          {isQueried && (
                            <span className="ml-2 text-[10px] text-zinc-400 font-sans font-medium">
                              (Queried Code)
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-zinc-300 font-mono text-[11px]">{link.short_description}</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2.5 py-0.5 bg-zinc-800 text-zinc-300 rounded-md text-[10px] font-medium border border-white/[0.06]">
                            {link.mapping_type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-emerald-400">
                          ₹{link.last_po_price?.toLocaleString() || "0"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {lookupResult && !lookupResult.found && (
        <div className="glass-card p-10 rounded-2xl text-center text-zinc-400 text-xs">
          No crosswalk record found for code <strong className="text-white font-mono">{searchQuery}</strong>.
        </div>
      )}
    </div>
  );
}
