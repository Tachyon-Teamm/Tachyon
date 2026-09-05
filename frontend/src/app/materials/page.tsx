"use client";

import { useEffect, useState, useCallback, Suspense, useMemo } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { api, API_BASE_URL } from "@/lib/api";
import { 
  Database, 
  Search, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight, 
  FilterX, 
  AlertCircle,
  X,
  Award,
  Download,
  CheckCircle2,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  ChevronDown
} from "lucide-react";

function MaterialsCatalogContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // URL-synchronized state defaults
  const initialSearch = searchParams.get("search") || "";
  const initialCpse = searchParams.get("cpse") || "";
  const initialTab = (searchParams.get("tab") as "GOLDEN" | "LOCAL") || "GOLDEN";
  const initialPage = parseInt(searchParams.get("page") || "1", 10);
  const initialPageSize = parseInt(searchParams.get("page_size") || "50", 10);

  const [activeTab, setActiveTab] = useState<"GOLDEN" | "LOCAL">(initialTab);
  const [materials, setMaterials] = useState<any[]>([]);
  const [goldenRecords, setGoldenRecords] = useState<any[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
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
  const [bannerMessage, setBannerMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [spotlightResult, setSpotlightResult] = useState<any | null>(null);

  // Sync state changes with browser URL
  const updateUrlParams = useCallback((newSearch: string, newCpse: string, newTab: string, newPage: number, newPageSize: number) => {
    const params = new URLSearchParams();
    if (newSearch) params.set("search", newSearch);
    if (newCpse) params.set("cpse", newCpse);
    if (newTab !== "GOLDEN") params.set("tab", newTab);
    if (newPage > 1) params.set("page", newPage.toString());
    if (newPageSize !== 50) params.set("page_size", newPageSize.toString());
    
    const queryString = params.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname, { scroll: false });
  }, [pathname, router]);

  // Load refineries on mount
  useEffect(() => {
    let isMounted = true;
    api.getRefineries()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setRefineries(data.map((r: any) => r.code));
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, []);

  const loadData = useCallback(async (
    targetTab = activeTab,
    targetPage = page, 
    targetPageSize = pageSize, 
    targetCpse = cpseFilter, 
    targetSearch = search
  ) => {
    setLoading(true);
    setError(null);
    try {
      // Trigger Bidirectional Crosswalk Spotlight Lookup in parallel if search query exists
      if (targetSearch && targetSearch.trim()) {
        api.reverseLookup(targetSearch.trim(), targetCpse || undefined)
          .then((rev) => {
            if (rev && rev.found && rev.cnmc_details) {
              setSpotlightResult(rev.cnmc_details);
            } else {
              setSpotlightResult(null);
            }
          })
          .catch(() => setSpotlightResult(null));
      } else {
        setSpotlightResult(null);
      }

      if (targetTab === "LOCAL") {
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
          setMaterials(data);
          setTotal(data.length);
          setTotalPages(1);
        }
      } else {
        const registry = await api.getCrosswalkRegistry();
        setGoldenRecords(registry || []);
        setTotal((registry || []).length);
      }
    } catch (err: any) {
      console.error("[Directory Load Error]:", err);
      setError(err?.message || "Failed to load directory records from server.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, cpseFilter, search, activeTab]);

  // Synchronize local component state whenever URL search parameters change (e.g. via Spotlight modal or navigation)
  useEffect(() => {
    const qSearch = searchParams.get("search") || "";
    const qCpse = searchParams.get("cpse") || "";
    const qTab = (searchParams.get("tab") as "GOLDEN" | "LOCAL") || "GOLDEN";
    const qPage = parseInt(searchParams.get("page") || "1", 10);
    const qPageSize = parseInt(searchParams.get("page_size") || "50", 10);

    setSearch(qSearch);
    setCpseFilter(qCpse);
    setActiveTab(qTab);
    setPage(qPage);
    setPageSize(qPageSize);

    loadData(qTab, qPage, qPageSize, qCpse, qSearch);
  }, [searchParams]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    updateUrlParams(search, cpseFilter, activeTab, 1, pageSize);
    loadData(activeTab, 1, pageSize, cpseFilter, search);
  };

  const handleResetFilters = () => {
    setSearch("");
    setCpseFilter("");
    setSpotlightResult(null);
    setPage(1);
    updateUrlParams("", "", activeTab, 1, pageSize);
    loadData(activeTab, 1, pageSize, "", "");
  };

  // Enterprise Export & Syndication Actions
  const handleExportCSV = (cpse?: string) => {
    const url = `${API_BASE_URL}/export/sap-lsmw-csv${cpse ? `?cpse_code=${cpse}` : ""}`;
    window.open(url, "_blank");
  };

  const handleSyncGeM = async () => {
    try {
      setBannerMessage(null);
      const res = await api.syncGeMCatalog();
      setBannerMessage({
        type: "success",
        text: `GeM Syndication: ${res.synced_count || res.message || "Catalog synchronized successfully with Government e-Marketplace."}`
      });
    } catch (err: any) {
      setBannerMessage({ type: "error", text: err.message || "Failed to sync with GeM API" });
    }
  };

  const handleExportSAP = async () => {
    try {
      setBannerMessage(null);
      const res = await api.exportSapIDoc();
      setBannerMessage({
        type: "success",
        text: `SAP IDoc Export: Generated MATMAS05 package (${res.idoc_control?.idoc_number || "MATMAS05-EXPORT"})`
      });
    } catch (err: any) {
      setBannerMessage({ type: "error", text: err.message || "Failed to generate SAP IDoc" });
    }
  };

  const handleVerifyChain = async () => {
    try {
      setBannerMessage(null);
      const res = await api.verifyAuditChain();
      setBannerMessage({
        type: "success",
        text: `Cryptographic Audit: Validated ${res.total_entries_verified} entries (${res.status})`
      });
    } catch (err: any) {
      setBannerMessage({ type: "error", text: err.message || "Audit chain verification failed" });
    }
  };

  // Filter Golden Records client-side for immediate responsive search
  const filteredGolden = useMemo(() => {
    if (!goldenRecords) return [];
    if (!search.trim()) return goldenRecords;
    const q = search.toLowerCase().trim();
    return goldenRecords.filter((g) => {
      const cnmc = (g.cnmc_code || "").toLowerCase();
      const desc = (g.golden_record?.standardized_description || "").toLowerCase();
      const links = (g.crosswalk_links || []).some(
        (l: any) =>
          (l.local_material_code || "").toLowerCase().includes(q) ||
          (l.cpse_code || "").toLowerCase().includes(q) ||
          (l.short_description || "").toLowerCase().includes(q)
      );
      return cnmc.includes(q) || desc.includes(q) || links;
    });
  }, [goldenRecords, search]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Executive Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <Database className="h-5 w-5 text-zinc-900 dark:text-zinc-100" />
            <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              National Master Directory
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 text-xs font-mono font-medium">
              {activeTab === "GOLDEN" ? `${filteredGolden.length} Masters` : `${total.toLocaleString()} Local Items`}
            </span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-2xl leading-relaxed">
            One Nation — One Material Code. Inspect authoritative Golden Records (CNMC) and bidirectional enterprise crosswalk linkages.
          </p>
        </div>

        {/* Integration Actions & Refresh */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Export & Syndication Menu */}
          <div className="relative inline-block text-left">
            <select
              onChange={(e) => {
                const act = e.target.value;
                if (act === "CSV") handleExportCSV(cpseFilter || undefined);
                if (act === "IDOC") handleExportSAP();
                if (act === "GEM") handleSyncGeM();
                if (act === "AUDIT") handleVerifyChain();
                e.target.value = "";
              }}
              defaultValue=""
              className="h-8.5 px-3 pr-8 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-medium cursor-pointer appearance-none transition apple-press"
            >
              <option value="" disabled>Export & Syndicate ▾</option>
              <option value="CSV">Export SAP LSMW (CSV)</option>
              <option value="IDOC">Export SAP IDoc (MATMAS05)</option>
              <option value="GEM">Syndicate to GeM Portal</option>
              <option value="AUDIT">Verify Cryptographic Audit Chain</option>
            </select>
          </div>

          <button
            onClick={() => loadData(activeTab, page, pageSize, cpseFilter, search)}
            disabled={loading}
            className="flex items-center space-x-1.5 h-8.5 px-3 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-medium apple-press transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Global Status Banner */}
      {bannerMessage && (
        <div className={`p-4 rounded-xl text-xs flex items-center justify-between border ${
          bannerMessage.type === "success" 
            ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/30 text-emerald-800 dark:text-emerald-200" 
            : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800/30 text-red-800 dark:text-red-200"
        }`}>
          <div className="flex items-center space-x-2.5">
            {bannerMessage.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
            )}
            <span>{bannerMessage.text}</span>
          </div>
          <button onClick={() => setBannerMessage(null)} className="font-bold px-2">✕</button>
        </div>
      )}

      {/* Spotlight Universal Search & Filter Bar */}
      <div className="glass-card p-4 rounded-2xl space-y-3">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          {/* Universal Search Input */}
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Spotlight: Search National CNMC, CPSE code (e.g. 100234), or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-9 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl pl-9 pr-14 text-xs text-zinc-900 dark:text-zinc-200 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 font-sans"
            />
            <Search className="h-4 w-4 text-zinc-400 absolute left-3 top-2.5" />
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono font-medium bg-zinc-200/80 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 absolute right-2.5 top-2">
              ⌘K
            </kbd>
          </div>

          {/* Segmented View Mode Toggle */}
          <div className="flex items-center p-0.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
            <button
              type="button"
              onClick={() => setActiveTab("GOLDEN")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === "GOLDEN" 
                  ? "bg-white dark:bg-zinc-800 text-zinc-950 dark:text-white shadow-sm font-semibold" 
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              <Award className="h-3.5 w-3.5 text-zinc-700 dark:text-zinc-300" />
              <span>National Golden (CNMC)</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("LOCAL")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === "LOCAL" 
                  ? "bg-white dark:bg-zinc-800 text-zinc-950 dark:text-white shadow-sm font-semibold" 
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              <Layers className="h-3.5 w-3.5 text-zinc-700 dark:text-zinc-300" />
              <span>CPSE Local Masters</span>
            </button>
          </div>

          {/* Optional Entity Filter for Local Records */}
          {activeTab === "LOCAL" && (
            <select
              value={cpseFilter}
              onChange={(e) => {
                setCpseFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-xl px-3 text-xs font-medium focus:outline-none"
            >
              <option value="">All CPSEs ({refineries.length})</option>
              {refineries.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          )}

          <div className="flex items-center space-x-2">
            <button
              type="submit"
              disabled={loading}
              className="h-9 px-4 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-950 rounded-xl text-xs font-semibold apple-press transition disabled:opacity-50"
            >
              Search
            </button>
            {(search || cpseFilter) && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="h-9 px-3 rounded-xl border border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200 text-xs apple-press transition"
                title="Reset Search & Filters"
              >
                <FilterX className="h-4 w-4" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Spotlight Bidirectional Authority Resolution Card */}
      {spotlightResult && (
        <div className="glass-card p-5 rounded-2xl border-2 border-emerald-500/30 dark:border-emerald-500/40 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-md space-y-3.5 animate-in fade-in duration-150">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-emerald-200/60 dark:border-emerald-800/40">
            <div className="flex items-center space-x-2.5">
              <span className="px-2 py-0.5 rounded-md bg-emerald-600 text-white font-mono text-[10px] font-bold tracking-wide">
                SPOTLIGHT RESOLUTION
              </span>
              <span className="text-sm font-mono font-bold text-zinc-900 dark:text-zinc-100">
                {spotlightResult.cnmc_code}
              </span>
              <span className="flex items-center text-[10px] text-emerald-700 dark:text-emerald-400 font-medium font-mono">
                <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-emerald-600 dark:text-emerald-400" />
                Governed National Standard (ISO 8000)
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setSelectedRecord({
                  cnmc_code: spotlightResult.cnmc_code,
                  golden_record: spotlightResult.golden_record,
                  crosswalk_links: spotlightResult.crosswalk_links,
                })}
                className="h-7 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium apple-press transition flex items-center space-x-1"
              >
                <span>Inspect in Master Drawer</span>
                <ArrowUpRight className="h-3 w-3" />
              </button>
              <button
                type="button"
                onClick={() => setSpotlightResult(null)}
                className="h-7 px-2 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition"
                title="Dismiss Spotlight Card"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="md:col-span-2 space-y-1">
              <span className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider block">
                Authoritative Description
              </span>
              <p className="text-xs font-sans text-zinc-900 dark:text-zinc-100 font-medium leading-relaxed">
                {spotlightResult.golden_record?.standardized_description || "—"}
              </p>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider block">
                Governed UOM & Benchmark
              </span>
              <p className="text-xs font-mono text-zinc-800 dark:text-zinc-200">
                Base UOM: <strong>{spotlightResult.golden_record?.base_uom || "EA"}</strong> · Spend: <strong>₹{Number(spotlightResult.total_spend || 0).toLocaleString()}</strong>
              </p>
            </div>
          </div>

          {/* Sibling Enterprise Crosswalk Linkages */}
          {spotlightResult.crosswalk_links?.length > 0 && (
            <div className="pt-2 border-t border-emerald-200/40 dark:border-emerald-800/30">
              <span className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider block mb-1.5">
                Resolved Sibling Crosswalk Linkages ({spotlightResult.crosswalk_links.length} Participating CPSEs)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {spotlightResult.crosswalk_links.map((link: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-white/80 dark:bg-zinc-900/80 border border-emerald-200/60 dark:border-zinc-800 text-xs space-y-1 shadow-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700">
                        {link.cpse_code}
                      </span>
                      <span className="font-mono text-[11px] font-semibold text-zinc-900 dark:text-zinc-100">
                        ₹{Number(link.last_po_price || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="font-mono text-[11px] text-zinc-900 dark:text-zinc-200 truncate">
                      {link.local_material_code}
                    </div>
                    <div className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">
                      {link.short_description}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Directory Table Surface */}
      <div className="glass-card rounded-2xl overflow-hidden shadow-sm">
        {activeTab === "GOLDEN" ? (
          /* National Golden Records View */
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-700 dark:text-zinc-300">
              <thead className="bg-zinc-50 dark:bg-zinc-950/60 text-zinc-500 uppercase font-medium border-b border-zinc-200 dark:border-zinc-800 text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4 font-mono">National Code (CNMC)</th>
                  <th className="py-3 px-4">Standardized Description (ISO 8000)</th>
                  <th className="py-3 px-4">Base UOM</th>
                  <th className="py-3 px-4">Linked CPSE Entities</th>
                  <th className="py-3 px-4 text-right">Governed Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200/70 dark:divide-zinc-800/70">
                {filteredGolden.map((g, idx) => (
                  <tr 
                    key={idx}
                    onClick={() => setSelectedRecord(g)}
                    className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4 font-mono font-semibold text-zinc-900 dark:text-zinc-100 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        <span>{g.cnmc_code}</span>
                        <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-sans text-zinc-800 dark:text-zinc-200 leading-relaxed max-w-md">
                      {g.golden_record?.standardized_description}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-zinc-600 dark:text-zinc-400">
                      {g.golden_record?.base_uom || "EA"}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {g.crosswalk_links?.map((link: any, lIdx: number) => (
                          <span
                            key={lIdx}
                            className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-100 dark:bg-zinc-800/90 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/60"
                          >
                            {link.cpse_code}: {link.local_material_code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-semibold text-zinc-900 dark:text-zinc-100 tabular-nums">
                      ₹{g.crosswalk_links?.[0]?.last_po_price?.toLocaleString() || "—"}
                    </td>
                  </tr>
                ))}
                {filteredGolden.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-zinc-500 font-sans text-xs">
                      No National Golden Records found matching your query.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          /* Local Records View */
          <div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-700 dark:text-zinc-300">
                <thead className="bg-zinc-50 dark:bg-zinc-950/60 text-zinc-500 uppercase font-medium border-b border-zinc-200 dark:border-zinc-800 text-[10px] tracking-wider">
                  <tr>
                    <th className="py-3 px-4">CPSE Entity</th>
                    <th className="py-3 px-4 font-mono">Local ERP Code</th>
                    <th className="py-3 px-4">Source Specification</th>
                    <th className="py-3 px-4">Normalized Attributes</th>
                    <th className="py-3 px-4">UOM</th>
                    <th className="py-3 px-4 text-right">Last PO Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200/70 dark:divide-zinc-800/70 font-mono">
                  {materials.map((m) => (
                    <tr
                      key={m.id}
                      onClick={() => setSelectedRecord({
                        cnmc_code: m.material_code,
                        golden_record: { standardized_description: m.short_description, base_uom: m.base_uom || m.uom },
                        crosswalk_links: [{
                          cpse_code: m.cpse_code,
                          local_material_code: m.material_code,
                          short_description: m.short_description,
                          last_po_price: m.last_po_price,
                          mapping_type: "LOCAL",
                        }],
                        local_material: m,
                      })}
                      className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                          {m.cpse_code}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-zinc-900 dark:text-zinc-100 whitespace-nowrap">
                        {m.material_code}
                      </td>
                      <td className="py-3.5 px-4 font-sans text-zinc-700 dark:text-zinc-300 max-w-md leading-relaxed">
                        {m.short_description}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[10px]">
                        <div className="flex flex-wrap gap-1">
                          {m.item_noun && (
                            <span className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700">
                              {m.item_noun}
                            </span>
                          )}
                          {m.nominal_size && (
                            <span className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700">
                              {m.nominal_size}
                            </span>
                          )}
                          {m.pressure_class && (
                            <span className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700">
                              {m.pressure_class}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-zinc-600 dark:text-zinc-400">
                        {m.uom}
                      </td>
                      <td className="py-3.5 px-4 text-right font-semibold text-zinc-900 dark:text-zinc-100 tabular-nums">
                        {m.last_po_price ? `₹${m.last_po_price.toLocaleString()}` : "—"}
                      </td>
                    </tr>
                  ))}
                  {materials.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500 font-sans text-xs">
                        No materials found matching your search.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {total > 0 && (
              <div className="p-4 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
                <div>
                  Page <span className="font-semibold text-zinc-900 dark:text-zinc-100">{page}</span> of {totalPages} ({total.toLocaleString()} items)
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="h-7 px-2.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 disabled:opacity-30 border border-zinc-200 dark:border-zinc-800 transition"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="h-7 px-2.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 disabled:opacity-30 border border-zinc-200 dark:border-zinc-800 transition"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Apple-Style Slide-over Inspector Sheet */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
          <div className="w-full max-w-xl h-full bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800 p-6 overflow-y-auto space-y-6 shadow-2xl flex flex-col justify-between">
            <div className="space-y-5">
              {/* Header */}
              <div className="flex items-center justify-between pb-4 border-b border-zinc-200 dark:border-zinc-800">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-md text-xs font-mono font-bold bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950">
                      {selectedRecord.cnmc_code}
                    </span>
                    <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center">
                      <ShieldCheck className="h-3.5 w-3.5 mr-1" /> Governed Record
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    Authoritative National Canonical Item
                  </p>
                </div>

                <button
                  onClick={() => setSelectedRecord(null)}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Standardized Description */}
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase font-mono font-semibold text-zinc-500 tracking-wider">
                  ISO 8000 Standardized Description:
                </span>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 leading-relaxed p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800/80">
                  {selectedRecord.golden_record?.standardized_description || selectedRecord.short_description}
                </p>
              </div>

              {/* Linked Sister CPSEs Crosswalk */}
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-mono font-semibold text-zinc-500 tracking-wider">
                  Multi-CPSE Linked Mappings (N:1 Equivalence):
                </span>
                <div className="rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800">
                  <table className="w-full text-left text-xs text-zinc-700 dark:text-zinc-300">
                    <thead className="bg-zinc-50 dark:bg-zinc-900/60 text-[10px] text-zinc-500 uppercase border-b border-zinc-200 dark:border-zinc-800">
                      <tr>
                        <th className="py-2.5 px-3 font-mono">Entity</th>
                        <th className="py-2.5 px-3 font-mono">ERP Code</th>
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3 text-right">Last PO</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200/60 dark:divide-zinc-800/60 font-mono">
                      {(selectedRecord.crosswalk_links || []).map((link: any, idx: number) => (
                        <tr key={idx} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/30">
                          <td className="py-2.5 px-3 font-bold text-zinc-900 dark:text-zinc-200">{link.cpse_code}</td>
                          <td className="py-2.5 px-3 text-zinc-600 dark:text-zinc-400">{link.local_material_code}</td>
                          <td className="py-2.5 px-3 font-sans text-xs text-zinc-800 dark:text-zinc-300 truncate max-w-[140px]" title={link.short_description}>
                            {link.short_description}
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-900 dark:text-zinc-100 font-semibold tabular-nums">
                            {link.last_po_price ? `₹${link.last_po_price.toLocaleString()}` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Bottom Actions Bar */}
            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <button
                type="button"
                onClick={() => handleExportCSV()}
                className="h-8.5 px-3.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-800 text-xs font-medium apple-press transition flex items-center space-x-1.5"
              >
                <Download className="h-3.5 w-3.5 text-zinc-500" />
                <span>Export SAP Format</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedRecord(null)}
                className="h-8.5 px-4 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950 text-xs font-semibold apple-press transition"
              >
                Done
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
        <div className="h-6 w-48 bg-zinc-200 dark:bg-zinc-800 rounded" />
        <div className="h-4 w-96 bg-zinc-100 dark:bg-zinc-800/60 rounded" />
        <div className="h-64 bg-zinc-50 dark:bg-zinc-800/30 rounded-xl" />
      </div>
    }>
      <MaterialsCatalogContent />
    </Suspense>
  );
}
