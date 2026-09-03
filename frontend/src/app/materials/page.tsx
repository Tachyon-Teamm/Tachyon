"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { 
  Database, 
  Search, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight, 
  FilterX, 
  AlertCircle,
  X,
  Layers,
  Award,
  Tag
} from "lucide-react";

function MaterialsCatalogContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // URL-synchronized state defaults
  const initialSearch = searchParams.get("search") || "";
  const initialCpse = searchParams.get("cpse") || "";
  const initialPage = parseInt(searchParams.get("page") || "1", 10);
  const initialPageSize = parseInt(searchParams.get("page_size") || "50", 10);

  const [activeTab, setActiveTab] = useState<"LOCAL" | "GOLDEN">("LOCAL");
  const [materials, setMaterials] = useState<any[]>([]);
  const [goldenRecords, setGoldenRecords] = useState<any[]>([]);
  const [selectedMaterial, setSelectedMaterial] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [search, setSearch] = useState(initialSearch);
  const [cpseFilter, setCpseFilter] = useState(initialCpse);
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [refineries, setRefineries] = useState<string[]>([
    "CPCL", "IOCL", "BPCL", "NTPC", "SAIL", "ONGC", "COALINDIA", "BHEL"
  ]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sync state changes with browser URL search parameters
  const updateUrlParams = useCallback((newSearch: string, newCpse: string, newPage: number, newPageSize: number) => {
    const params = new URLSearchParams();
    if (newSearch) params.set("search", newSearch);
    if (newCpse) params.set("cpse", newCpse);
    if (newPage > 1) params.set("page", newPage.toString());
    if (newPageSize !== 50) params.set("page_size", newPageSize.toString());
    
    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname, { scroll: false });
  }, [pathname, router]);

  // Fetch dynamic refineries list from database
  useEffect(() => {
    let isMounted = true;
    api.getRefineries()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setRefineries(data.map((r: any) => r.code));
        }
      })
      .catch(() => {
        // Graceful fallback to default refinery list
      });
    return () => { isMounted = false; };
  }, []);

  const loadMaterials = useCallback(async (
    targetPage = page, 
    targetPageSize = pageSize, 
    targetCpse = cpseFilter, 
    targetSearch = search
  ) => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "LOCAL") {
        const data = await api.getMaterials({
          cpse_code: targetCpse || undefined,
          search: targetSearch || undefined,
          page: targetPage,
          page_size: targetPageSize,
        });

        if (data && Array.isArray(data.items)) {
          setMaterials(data.items);
          setTotal(data.total);
          setTotalPages(data.total_pages);
          setPage(data.page);
        } else if (Array.isArray(data)) {
          // Fallback in case of raw list response
          setMaterials(data);
          setTotal(data.length);
          setTotalPages(1);
        }
      } else {
        const registry = await api.getCrosswalkRegistry();
        setGoldenRecords(registry);
        setTotal(registry.length);
      }
    } catch (err: any) {
      console.error("[Materials Catalog Error]:", err);
      setError(err?.message || "Failed to fetch materials catalog from the server.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, cpseFilter, search, activeTab]);

  useEffect(() => {
    loadMaterials(page, pageSize, cpseFilter, search);
    updateUrlParams(search, cpseFilter, page, pageSize);
  }, [page, pageSize, cpseFilter, activeTab]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadMaterials(1, pageSize, cpseFilter, search);
    updateUrlParams(search, cpseFilter, 1, pageSize);
  };

  const handleCpseChange = (val: string) => {
    setCpseFilter(val);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSearch("");
    setCpseFilter("");
    setPage(1);
    loadMaterials(1, pageSize, "", "");
    updateUrlParams("", "", 1, pageSize);
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
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {total.toLocaleString()} Items Indexed
            </span>
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
            onClick={() => loadMaterials(page, pageSize, cpseFilter, search)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium apple-press transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-white" : ""}`} />
            <span>Refresh Catalog</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 rounded-2xl">
        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          <div className={activeTab === "LOCAL" ? "sm:col-span-2" : "sm:col-span-4"}>
            <div className="relative">
              <input
                type="text"
                placeholder={activeTab === "LOCAL" ? "Search by code, keyword, part no, or noun (e.g. valve, pipe, 6205)..." : "Search CNMC Code or Golden Description..."}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full glass-input text-white rounded-xl pl-9 pr-4 py-2.5 text-xs focus:outline-none"
              />
              <Search className="h-3.5 w-3.5 text-zinc-400 absolute left-3 top-3" />
            </div>
          </div>

          {activeTab === "LOCAL" && (
            <div>
              <select
                value={cpseFilter}
                onChange={(e) => handleCpseChange(e.target.value)}
                className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
              >
                <option value="">All CPSEs ({refineries.length})</option>
                {refineries.map((ref) => (
                  <option key={ref} value={ref}>{ref}</option>
                ))}
              </select>
            </div>
          )}

          {activeTab === "LOCAL" && (
            <div>
              <select
                value={pageSize}
                onChange={(e) => {
                  const newSize = parseInt(e.target.value, 10);
                  setPageSize(newSize);
                  setPage(1);
                }}
                className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
              >
                <option value={25}>25 / page</option>
                <option value={50}>50 / page</option>
                <option value={100}>100 / page</option>
              </select>
            </div>
          )}

          <div className="flex space-x-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press transition disabled:opacity-50"
            >
              <Search className="h-3.5 w-3.5 text-black" />
              <span>Search</span>
            </button>
            {(search || cpseFilter) && (
              <button
                type="button"
                onClick={handleResetFilters}
                title="Reset all filters"
                className="px-3 py-2.5 glass-input hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-xl text-xs apple-press transition"
              >
                <FilterX className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-between text-xs text-red-300">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadMaterials(page, pageSize, cpseFilter, search)}
            className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-red-200 text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {/* Table */}
      <div className="glass-card rounded-2xl overflow-hidden shadow-sm">
        {activeTab === "LOCAL" ? (
          <div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                  <tr>
                    <th className="py-3.5 px-4">CPSE</th>
                    <th className="py-3.5 px-4">Local Code</th>
                    <th className="py-3.5 px-4">Source Specification</th>
                    <th className="py-3.5 px-4">Deterministic Extracted Specs</th>
                    <th className="py-3.5 px-4">UOM</th>
                    <th className="py-3.5 px-4 text-right">Last PO Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono">
                  {loading ? (
                    Array.from({ length: 6 }).map((_, idx) => (
                      <tr key={`skeleton-${idx}`} className="animate-pulse">
                        <td className="py-4 px-4"><div className="h-5 w-12 bg-zinc-800/80 rounded-full" /></td>
                        <td className="py-4 px-4"><div className="h-4 w-24 bg-zinc-800/80 rounded" /></td>
                        <td className="py-4 px-4"><div className="h-4 w-64 bg-zinc-800/80 rounded" /></td>
                        <td className="py-4 px-4">
                          <div className="flex gap-1.5">
                            <div className="h-4 w-16 bg-zinc-800/80 rounded" />
                            <div className="h-4 w-20 bg-zinc-800/80 rounded" />
                          </div>
                        </td>
                        <td className="py-4 px-4"><div className="h-4 w-8 bg-zinc-800/80 rounded" /></td>
                        <td className="py-4 px-4 text-right"><div className="h-4 w-16 bg-zinc-800/80 rounded ml-auto" /></td>
                      </tr>
                    ))
                  ) : materials.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-400 font-sans">
                        <div className="flex flex-col items-center justify-center space-y-2">
                          <FilterX className="h-8 w-8 text-zinc-500" />
                          <p className="text-sm font-semibold text-zinc-200">No materials found</p>
                          <p className="text-xs text-zinc-500 max-w-sm">
                            No catalog items matched your active search criteria. Try modifying your search keywords or clearing the filter.
                          </p>
                          {(search || cpseFilter) && (
                            <button
                              onClick={handleResetFilters}
                              className="mt-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-xs font-medium"
                            >
                              Clear Filters
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ) : (
                    materials.map((m) => (
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
                          <div className="flex items-center space-x-1.5">
                            <span>{m.material_code}</span>
                            {m.status && m.status !== "ACTIVE" && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                {m.status}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-300 text-[11px] font-sans font-medium max-w-md">
                          {m.short_description}
                        </td>
                        <td className="py-3.5 px-4 font-sans">
                          <div className="flex flex-wrap gap-1">
                            {m.item_noun && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]" title="Item Noun">
                                {m.item_noun}
                              </span>
                            )}
                            {m.nominal_size && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-cyan-300 rounded-md text-[10px] border border-cyan-500/20 font-medium" title="Nominal Size">
                                {m.nominal_size}
                              </span>
                            )}
                            {m.pressure_class && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-amber-300 rounded-md text-[10px] border border-amber-500/20 font-medium" title="Pressure Class">
                                {m.pressure_class}
                              </span>
                            )}
                            {m.moc && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-purple-300 rounded-md text-[10px] border border-purple-500/20 font-medium" title="MOC">
                                {m.moc}
                              </span>
                            )}
                            {m.schedule && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-orange-300 rounded-md text-[10px] border border-orange-500/20 font-semibold" title="Schedule">
                                {m.schedule}
                              </span>
                            )}
                            {m.end_connection && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded-md text-[10px] border border-white/[0.06]" title="End Connection">
                                {m.end_connection}
                              </span>
                            )}
                            {m.package_multiplier > 1.0 && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] font-semibold border border-white/[0.06]" title="Multiplier">
                                {m.package_multiplier}x
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-zinc-300 font-sans">
                          <span>{m.uom}</span>
                          {m.base_uom && m.base_uom !== m.uom && (
                            <span className="text-[10px] text-zinc-500 block font-normal">
                              ({m.base_uom})
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right font-bold text-emerald-400 font-mono">
                          {m.last_po_price != null ? `₹${m.last_po_price.toLocaleString()}` : "N/A"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Bar */}
            {total > 0 && (
              <div className="p-4 bg-zinc-950/80 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-zinc-400">
                <div>
                  Showing <span className="font-semibold text-white">{((page - 1) * pageSize) + 1}</span> to{" "}
                  <span className="font-semibold text-white">{Math.min(page * pageSize, total)}</span> of{" "}
                  <span className="font-semibold text-white">{total.toLocaleString()}</span> items
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1 || loading}
                    className="flex items-center space-x-1 px-3 py-1.5 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed apple-press transition"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    <span>Prev</span>
                  </button>

                  <span className="px-3 py-1.5 bg-zinc-900 border border-white/[0.08] rounded-xl text-xs font-mono text-zinc-200">
                    Page {page} of {totalPages}
                  </span>

                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages || loading}
                    className="flex items-center space-x-1 px-3 py-1.5 glass-input hover:bg-zinc-800 text-zinc-300 rounded-xl text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed apple-press transition"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
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

export default function MaterialsPage() {
  return (
    <Suspense fallback={
      <div className="space-y-4 p-6 glass-card rounded-2xl animate-pulse">
        <div className="h-6 w-48 bg-zinc-800 rounded" />
        <div className="h-4 w-96 bg-zinc-800/60 rounded" />
        <div className="h-64 bg-zinc-800/30 rounded-xl" />
      </div>
    }>
      <MaterialsCatalogContent />
    </Suspense>
  );
}

