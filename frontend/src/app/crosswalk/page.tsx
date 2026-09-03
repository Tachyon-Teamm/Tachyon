"use client";

import { useState, useEffect } from "react";
import { api, API_BASE_URL } from "@/lib/api";
import { 
  Layers, 
  Search, 
  Download, 
  CheckCircle2,
  AlertCircle
} from "lucide-react";

export default function CrosswalkPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCPSE, setSelectedCPSE] = useState("");
  const [availableCpses, setAvailableCpses] = useState<{ id: number; code: string; name: string }[]>([]);
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [registryList, setRegistryList] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [auditStatus, setAuditStatus] = useState<any | null>(null);

  const loadRegistry = async () => {
    setRegistryLoading(true);
    try {
      const data = await api.getCrosswalkRegistry();
      setRegistryList(data);
    } catch (err) {
      console.error("Failed to load crosswalk registry", err);
    } finally {
      setRegistryLoading(false);
    }
  };

  useEffect(() => {
    loadRegistry();
  }, []);

  useEffect(() => {
    let isMounted = true;
    api.getCpses()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setAvailableCpses(data);
        }
      })
      .catch((err) => {
        console.warn("[Crosswalk] Failed to load dynamic CPSE list:", err);
      });
    return () => { isMounted = false; };
  }, []);

  const handleSearch = async (e?: React.FormEvent, overrideCode?: string, overrideCPSE?: string) => {
    if (e) e.preventDefault();
    const codeToSearch = (overrideCode !== undefined ? overrideCode : searchQuery).trim();
    const cpseToSearch = (overrideCPSE !== undefined ? overrideCPSE : selectedCPSE).trim();
    if (!codeToSearch) return;

    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.reverseLookup(codeToSearch, cpseToSearch || undefined);
      setLookupResult(res);
    } catch (err: any) {
      console.error(err);
      setLookupResult(null);
      setErrorMessage(err.message || "Failed to resolve code. Please verify network connectivity and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = (cpse?: string) => {
    const url = `${API_BASE_URL}/export/sap-lsmw-csv${cpse ? `?cpse_code=${cpse}` : ""}`;
    window.open(url, "_blank");
  };

  const handleSyncGeM = async () => {
    try {
      setSuccessMessage(null);
      const res = await api.syncGeMCatalog();
      setSuccessMessage(`Government e-Marketplace (GeM) Sync: ${res.synced_count || res.message || "Catalog synchronized successfully."}`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to sync with GeM API");
    }
  };

  const handleExportSAP = async () => {
    try {
      setSuccessMessage(null);
      const res = await api.exportSapIDoc();
      setSuccessMessage(`SAP Integration: Generated MATMAS05 IDoc batch (${res.idoc_control?.idoc_number || "MATMAS05-EXPORT"})`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to generate SAP IDoc");
    }
  };

  const handleVerifyChain = async () => {
    try {
      const res = await api.verifyAuditChain();
      setAuditStatus(res);
      setSuccessMessage(`CERT-In Cryptographic Audit: Validated ${res.total_entries_verified} entries (${res.status})`);
    } catch (err: any) {
      setErrorMessage(err.message || "Audit chain verification failed");
    }
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
            Search any legacy CPSE material code OR authoritative National CNMC code to resolve crosswalk mappings.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSyncGeM}
            className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-semibold apple-press transition"
          >
            <span>Syndicate to GeM</span>
          </button>
          <button
            onClick={handleExportSAP}
            className="flex items-center space-x-1.5 px-3 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 rounded-xl text-xs font-semibold apple-press transition"
          >
            <span>Export SAP IDoc</span>
          </button>
          <button
            onClick={handleVerifyChain}
            className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-semibold apple-press transition"
          >
            <span>Verify Audit Chain</span>
          </button>
          <button
            onClick={() => handleExportCSV(selectedCPSE || undefined)}
            className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-semibold apple-press transition shadow-sm"
            title={selectedCPSE ? `Export SAP LSMW CSV filtered for ${selectedCPSE}` : "Export National SAP LSMW CSV across all entities"}
          >
            <Download className="h-3.5 w-3.5" />
            <span>{selectedCPSE ? `Export ${selectedCPSE} SAP CSV` : "Export National SAP CSV"}</span>
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMessage && (
        <div className="flex items-center space-x-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="flex items-center justify-between p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-red-400 hover:text-red-200 text-xs font-bold px-2 py-0.5 rounded transition"
            title="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Spotlight Search Box */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider block">
          Bidirectional Code Lookup & N:1 Crosswalk Resolver
        </span>

        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <input
              type="text"
              placeholder="Enter Local Code (e.g. 100234, 889102) or National Code (e.g. CNMC-00000001-7)..."
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
              <option value="">All Entities / Nationwide</option>
              {availableCpses.map((cpse) => (
                <option key={cpse.code} value={cpse.code}>
                  {cpse.code} {cpse.name ? `(${cpse.name})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press transition"
            >
              <Search className="h-3.5 w-3.5 text-black" />
              <span>{loading ? "Resolving..." : "Lookup Code"}</span>
            </button>
          </div>
        </form>
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
                          {isQueried ? (
                            <div className="flex items-center">
                              <span>{link.local_material_code}</span>
                              <span className="ml-2 px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-white/[0.08] text-[10px] font-sans font-medium">
                                (Queried Code)
                              </span>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setSearchQuery(link.local_material_code);
                                setSelectedCPSE(link.cpse_code);
                                handleSearch(undefined, link.local_material_code, link.cpse_code);
                              }}
                              className="text-left font-mono hover:text-blue-400 hover:underline transition-colors flex items-center group cursor-pointer"
                              title={`Click to pivot search to ${link.cpse_code} code: ${link.local_material_code}`}
                            >
                              <span>{link.local_material_code}</span>
                              <span className="ml-2 text-[10px] text-zinc-500 group-hover:text-blue-400 font-sans font-normal">
                                (Click to query)
                              </span>
                            </button>
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

      {/* Complete National Master Crosswalk Registry Table */}
      <div className="glass-card rounded-2xl overflow-hidden shadow-sm space-y-3 p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold tracking-tight text-white flex items-center space-x-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              <span>Registered National Crosswalk Mappings</span>
            </h2>
            <p className="text-xs text-zinc-400">
              Authoritative single-source crosswalk directory connecting CPSE catalogs to National CNMC codes.
            </p>
          </div>
          <span className="text-xs font-mono text-zinc-400">
            {registryList.length} Active Master Codes
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
              <tr>
                <th className="py-3 px-4">Authoritative CNMC</th>
                <th className="py-3 px-4">Harmonized ISO 8000 Description</th>
                <th className="py-3 px-4">Base UOM</th>
                <th className="py-3 px-4">Mapped CPSE Entities & Codes</th>
                <th className="py-3 px-4 text-right">Registered Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {registryList.map((entry, idx) => (
                <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                    <button
                      onClick={() => handleSearch(undefined, entry.cnmc_code)}
                      className="hover:underline text-left cursor-pointer"
                    >
                      {entry.cnmc_code}
                    </button>
                  </td>
                  <td className="py-3.5 px-4 font-sans text-white text-[12px]">
                    {entry.golden_record?.standardized_description || "—"}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-zinc-300">
                    {entry.golden_record?.base_uom || "EA"}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex flex-wrap gap-1">
                      {entry.crosswalk_links?.map((link: any, lIdx: number) => (
                        <span
                          key={lIdx}
                          onClick={() => handleSearch(undefined, link.local_material_code, link.cpse_code)}
                          className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 hover:bg-zinc-700 cursor-pointer text-zinc-200 border border-white/[0.06] transition"
                          title={`Click to lookup: ${link.cpse_code} ${link.short_description}`}
                        >
                          {link.cpse_code}: {link.local_material_code} ({link.mapping_type || "EQUIV"})
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-zinc-400 text-[11px]">
                    {entry.issued_at ? new Date(entry.issued_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
              {registryList.length === 0 && !registryLoading && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-zinc-500">
                    No approved crosswalk records in registry yet. Review and approve candidate clusters in the Review Queue to mint CNMC codes.
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
