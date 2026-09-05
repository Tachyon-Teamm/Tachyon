"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  Search, 
  Database, 
  CheckCircle2, 
  ArrowRight, 
  X, 
  UploadCloud, 
  GitMerge, 
  BarChart3
} from "lucide-react";
import { api } from "@/lib/api";

interface SpotlightModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SpotlightModal({ isOpen, onClose }: SpotlightModalProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [lookupResult, setLookupResult] = useState<any | null>(null);
  const [matchingMaterials, setMatchingMaterials] = useState<any[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open with clean cancellation
  useEffect(() => {
    let focusTimer: any;
    if (isOpen) {
      focusTimer = setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setLookupResult(null);
      setMatchingMaterials([]);
    }
    return () => clearTimeout(focusTimer);
  }, [isOpen]);

  // Global keydown listeners for Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Debounced search with isCurrent cancellation guard against network race conditions
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setLookupResult(null);
      setMatchingMaterials([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    let isCurrent = true;

    const timer = setTimeout(async () => {
      try {
        const [lookup, materialsData] = await Promise.allSettled([
          api.reverseLookup(trimmed).catch(() => null),
          api.getMaterials({ search: trimmed, page_size: 6 }).catch(() => null)
        ]);

        if (!isCurrent) return;

        if (lookup.status === "fulfilled" && lookup.value && lookup.value.found) {
          setLookupResult(lookup.value);
        } else {
          setLookupResult(null);
        }

        if (materialsData.status === "fulfilled" && materialsData.value) {
          const items = Array.isArray(materialsData.value) 
            ? materialsData.value 
            : (materialsData.value as any)?.items || [];
          setMatchingMaterials(items.slice(0, 5));
        } else {
          setMatchingMaterials([]);
        }
      } catch (err) {
        console.error("Spotlight search error:", err);
      } finally {
        if (isCurrent) {
          setLoading(false);
        }
      }
    }, 220);

    return () => {
      isCurrent = false;
      clearTimeout(timer);
    };
  }, [query]);

  if (!isOpen) return null;

  const quickNav = [
    { title: "National Master Directory", subtitle: "Inspect Golden Records & CPSE Linkages", href: "/materials", icon: Database },
    { title: "Governance Review Queue", subtitle: "Compare match candidates & mint CNMC codes", href: "/review", icon: GitMerge },
    { title: "Import & Harmonize", subtitle: "Upload enterprise SAP/Oracle catalog extracts", href: "/ingestion", icon: UploadCloud },
    { title: "Analytics & Sourcing", subtitle: "Demand aggregation & standardization KPIs", href: "/", icon: BarChart3 },
  ];

  const handleSelectNav = (href: string) => {
    router.push(href);
    onClose();
  };

  const handleSelectMaterial = (mat: any) => {
    router.push(`/materials?search=${encodeURIComponent(mat.material_code)}&tab=LOCAL`);
    onClose();
  };

  const handleSelectCNMC = (cnmcCode: string) => {
    router.push(`/materials?search=${encodeURIComponent(cnmcCode)}&tab=GOLDEN`);
    onClose();
  };

  // Keyboard execution contract for Enter key
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (lookupResult && lookupResult.found && lookupResult.cnmc_details) {
        handleSelectCNMC(lookupResult.cnmc_details.cnmc_code);
      } else if (matchingMaterials.length > 0) {
        handleSelectMaterial(matchingMaterials[0]);
      } else if (query.trim()) {
        router.push(`/materials?search=${encodeURIComponent(query.trim())}&tab=GOLDEN`);
        onClose();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 sm:pt-28 px-4 bg-black/60 backdrop-blur-md transition-opacity animate-in fade-in duration-150">
      {/* Backdrop Dismiss Area */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Spotlight Window */}
      <div className="relative w-full max-w-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden z-10 animate-in zoom-in-95 duration-150">
        {/* Search Header */}
        <div className="flex items-center px-4 py-3.5 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <Search className="h-5 w-5 text-zinc-400 dark:text-zinc-500 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Spotlight: Type National Code, CPSE code (e.g. 100234), or keyword..."
            className="w-full bg-transparent text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none font-sans"
          />
          {loading && (
            <div className="h-4 w-4 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin mr-2 shrink-0" />
          )}
          {query && !loading && (
            <button
              onClick={() => setQuery("")}
              className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition mr-2"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
            ESC
          </span>
        </div>

        {/* Results Container */}
        <div className="max-h-[60vh] overflow-y-auto p-3 space-y-4">
          {/* 1. Bidirectional Resolved CNMC Authority Card */}
          {lookupResult && lookupResult.found && lookupResult.cnmc_details && (
            <div className="p-3.5 bg-emerald-500/10 dark:bg-emerald-950/30 border border-emerald-500/20 rounded-xl space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-emerald-700 dark:text-emerald-400">
                    Resolved National Authority
                  </span>
                  <span className="flex items-center text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 font-medium font-mono">
                    <CheckCircle2 className="h-3 w-3 mr-1" /> Governed CNMC
                  </span>
                </div>
                <button
                  onClick={() => handleSelectCNMC(lookupResult.cnmc_details.cnmc_code)}
                  className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:underline flex items-center space-x-1"
                >
                  <span>Inspect in Directory</span>
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>

              <div className="flex items-baseline space-x-3">
                <span className="text-base font-mono font-bold text-zinc-900 dark:text-white">
                  {lookupResult.cnmc_details.cnmc_code}
                </span>
                <span className="text-xs text-zinc-600 dark:text-zinc-300 font-medium">
                  {lookupResult.cnmc_details.golden_record?.standardized_description}
                </span>
              </div>

              {/* Sister Crosswalk Links */}
              {lookupResult.cnmc_details.crosswalk_links?.length > 0 && (
                <div className="pt-2 border-t border-emerald-500/20 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] text-zinc-500 dark:text-zinc-400 mr-1">Linked CPSEs:</span>
                  {lookupResult.cnmc_details.crosswalk_links.map((link: any, lIdx: number) => (
                    <span
                      key={lIdx}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-emerald-500/20 shadow-xs"
                    >
                      <strong className="font-semibold">{link.cpse_code}</strong>: {link.local_material_code}
                      {link.last_po_price ? ` (₹${Number(link.last_po_price).toLocaleString()})` : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 2. CPSE Local Materials Matches */}
          {matchingMaterials.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider px-2">
                Matching Catalog Items ({matchingMaterials.length})
              </span>
              <div className="space-y-1">
                {matchingMaterials.map((m) => (
                  <div
                    key={m.id}
                    onClick={() => handleSelectMaterial(m)}
                    className="flex items-center justify-between p-2.5 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800/70 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-zinc-200/70 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border border-zinc-300/50 dark:border-zinc-700">
                        {m.cpse_code}
                      </span>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 font-mono group-hover:text-black dark:group-hover:text-white truncate">
                          {m.material_code}
                        </div>
                        <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate max-w-md">
                          {m.short_description}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0">
                      {m.last_po_price && (
                        <span className="text-xs font-mono font-medium text-zinc-700 dark:text-zinc-300">
                          ₹{Number(m.last_po_price).toLocaleString()}
                        </span>
                      )}
                      <ArrowRight className="h-3.5 w-3.5 text-zinc-400 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. Empty State with Query */}
          {query.trim() && !loading && !lookupResult?.found && matchingMaterials.length === 0 && (
            <div className="py-8 text-center space-y-1">
              <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
                No matching materials or crosswalk linkages found for &quot;{query}&quot;
              </p>
              <p className="text-[11px] text-zinc-400">
                Try searching by exact CPSE code (e.g. 100234), CNMC code, or item noun (Valve, Bearing).
              </p>
            </div>
          )}

          {/* 4. Quick Navigation & System Verbs */}
          {(!query.trim() || matchingMaterials.length === 0) && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider px-2">
                Quick Navigation & Workflows
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {quickNav.map((item) => (
                  <div
                    key={item.href}
                    onClick={() => handleSelectNav(item.href)}
                    className="flex items-center space-x-3 p-2.5 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800/70 transition-colors cursor-pointer group border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700"
                  >
                    <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 group-hover:bg-zinc-200 dark:group-hover:bg-zinc-700 transition">
                      <item.icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        {item.title}
                      </div>
                      <div className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Shortcut Hints */}
        <div className="px-4 py-2.5 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-500">
          <div className="flex items-center space-x-3 font-mono">
            <span><strong className="text-zinc-700 dark:text-zinc-300">↵</strong> Select</span>
            <span><strong className="text-zinc-700 dark:text-zinc-300">esc</strong> Close</span>
          </div>
          <span className="font-sans text-[10px] text-zinc-400">
            Bidirectional N:1 Crosswalk Resolver Active
          </span>
        </div>
      </div>
    </div>
  );
}
