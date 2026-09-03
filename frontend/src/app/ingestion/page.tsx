"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  UploadCloud, 
  CheckCircle2, 
  ArrowRight, 
  AlertCircle, 
  RefreshCw, 
  FileCheck2,
  Layers
} from "lucide-react";

export default function IngestionPage() {
  const [cpses, setCpses] = useState<{ id: number; code: string; name: string; sector?: string }[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [selectedCPSE, setSelectedCPSE] = useState<string>("IOCL");
  const [file, setFile] = useState<File | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [detectData, setDetectData] = useState<any>(null);
  const [mappingConfig, setMappingConfig] = useState<Record<string, string>>({});
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [isStartingBatch, setIsStartingBatch] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<any>(null);
  const [progressInfo, setProgressInfo] = useState<{ id: number; processed: number; total: number; percent: number; status: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadCpsesAndBatches = useCallback(async () => {
    try {
      const [cpseList, batchList] = await Promise.all([
        api.getCpses().catch(() => []),
        api.getBatches().catch(() => [])
      ]);
      if (cpseList && cpseList.length > 0) {
        setCpses(cpseList);
      }
      if (batchList) {
        setBatches(batchList);
      }
    } catch (err) {
      console.error("Initial load error:", err);
    }
  }, []);

  useEffect(() => {
    loadCpsesAndBatches();
  }, [loadCpsesAndBatches]);

  // Periodic polling for active background batch executions
  useEffect(() => {
    const hasActive = batches.some((b) => b.status === "PENDING" || b.status === "PROCESSING");
    if (!hasActive && progressInfo?.status !== "PROCESSING") return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.getBatches();
        setBatches(updated);
      } catch (e) {
        // silent background poll error
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [batches, progressInfo]);

  const handleCPSEChange = async (newCPSE: string) => {
    setSelectedCPSE(newCPSE);
    if (file) {
      setIsDetecting(true);
      setErrorMsg(null);
      setBatchResult(null);
      try {
        const res = await api.detectColumns(file, newCPSE);
        setDetectData(res);
        setUploadId(res.upload_id || null);
        setMappingConfig(res.suggested_mappings || {});
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to re-detect columns for selected refinery");
      } finally {
        setIsDetecting(false);
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setErrorMsg(null);
      setDetectData(null);
      setUploadId(null);
      setBatchResult(null);
      setProgressInfo(null);

      setIsDetecting(true);
      try {
        const res = await api.detectColumns(selected, selectedCPSE);
        setDetectData(res);
        setUploadId(res.upload_id || null);
        setMappingConfig(res.suggested_mappings || {});
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to detect columns from file");
      } finally {
        setIsDetecting(false);
      }
    }
  };

  const loadSample = async (cpse: string) => {
    setSelectedCPSE(cpse);
    setIsDetecting(true);
    setErrorMsg(null);
    setBatchResult(null);
    setProgressInfo(null);
    setUploadId(null);
    try {
      const samples = await api.getSamples();
      const sampleItem = samples?.[cpse] || samples?.["IOCL"];
      if (!sampleItem || !sampleItem.content) {
        throw new Error(`Sample extract for ${cpse} not found on server.`);
      }
      const realFile = new File(
        [sampleItem.content], 
        sampleItem.filename || `${cpse.toLowerCase()}_sample_extract.csv`, 
        { type: "text/csv" }
      );
      setFile(realFile);
      const res = await api.detectColumns(realFile, cpse);
      setDetectData(res);
      setUploadId(res.upload_id || null);
      setMappingConfig(res.suggested_mappings || {});
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load sample from server");
    } finally {
      setIsDetecting(false);
    }
  };

  const handleMappingChange = async (sourceCol: string, targetField: string) => {
    const newMapping = {
      ...mappingConfig,
      [sourceCol]: targetField,
    };
    setMappingConfig(newMapping);

    if (detectData && detectData.preview_rows && detectData.preview_rows.length > 0) {
      try {
        const previewRes = await api.recalculatePreview(detectData.preview_rows, newMapping);
        if (previewRes && previewRes.preview_rows) {
          setDetectData((prev: any) => ({
            ...prev,
            preview_rows: previewRes.preview_rows,
            quality_score: previewRes.quality_score ?? prev.quality_score,
          }));
        }
      } catch (err) {
        // Continue silently if preview recalculation fails
      }
    }
  };

  // Derive mapping validation and target field counts
  const targetCounts = Object.entries(mappingConfig).reduce((acc, [col, target]) => {
    if (target !== "unmapped") {
      acc[target] = (acc[target] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  const duplicateTargets = Object.entries(targetCounts)
    .filter(([_, count]) => count > 1)
    .map(([target]) => target);
  const hasDuplicateTargets = duplicateTargets.length > 0;
  const isMaterialCodeMapped = Object.values(mappingConfig).includes("material_code");
  const isShortDescMapped = Object.values(mappingConfig).includes("short_description");
  const canStartBatch = isMaterialCodeMapped && isShortDescMapped && !hasDuplicateTargets;

  // Dynamically resolve source column mapped to description and uom
  const descColumn = Object.entries(mappingConfig).find(([_, target]) => target === "short_description")?.[0];
  const uomColumn = Object.entries(mappingConfig).find(([_, target]) => target === "uom")?.[0];

  const handleStartBatch = async () => {
    if (!detectData || !canStartBatch) return;
    setIsStartingBatch(true);
    setErrorMsg(null);
    setProgressInfo(null);

    try {
      const res = await api.startBatch(file, selectedCPSE, JSON.stringify(mappingConfig), uploadId || undefined);
      setBatchResult(res);
      setProgressInfo({
        id: res.id,
        processed: res.processed_rows || 0,
        total: res.total_rows || 0,
        percent: 0,
        status: res.status || "PROCESSING"
      });

      // Instantly refresh batch history
      api.getBatches().then(setBatches).catch(() => {});

      // Poll background worker progress
      const pollTimer = setInterval(async () => {
        try {
          const statusRes = await api.getBatchStatus(res.id);
          setProgressInfo({
            id: statusRes.id,
            processed: statusRes.processed_rows,
            total: statusRes.total_rows,
            percent: statusRes.percent_complete,
            status: statusRes.status
          });

          if (statusRes.status === "COMPLETED" || statusRes.status === "FAILED") {
            clearInterval(pollTimer);
            setIsStartingBatch(false);
            setBatchResult((prev: any) => ({ ...prev, status: statusRes.status, processed_rows: statusRes.processed_rows }));
            api.getBatches().then(setBatches).catch(() => {});
          }
        } catch (pollErr) {
          console.error("Batch polling error:", pollErr);
        }
      }, 1500);

    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start batch ingestion");
      setIsStartingBatch(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-card p-6 rounded-2xl">
        <div className="flex items-center space-x-2.5 mb-1">
          <UploadCloud className="h-5 w-5 text-zinc-300" />
          <h1 className="text-xl font-bold tracking-tight text-white">
            Ingestion & Column Mapper
          </h1>
        </div>
        <p className="text-xs text-zinc-400 font-normal">
          Upload SAP ERP extracts (CSV / Excel). Automatic header detection, 5-row live normalization preview, and batch processing.
        </p>
      </div>

      {/* Step 1: Upload & CPSE Selection */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider block">
            Step 1 • Select Refinery & Upload Material Master Extract
          </span>
          <span className="text-[11px] text-zinc-500">Supported: CSV, XLSX, XLS</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-medium text-zinc-300 block mb-1.5">Target CPSE Entity</label>
            <select
              value={selectedCPSE}
              onChange={(e) => handleCPSEChange(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
            >
              {cpses.length > 0 ? (
                Object.entries(
                  cpses.reduce((acc, c) => {
                    const sec = c.sector ? c.sector.replace(/_/g, " ") : "GENERAL";
                    acc[sec] = acc[sec] || [];
                    acc[sec].push(c);
                    return acc;
                  }, {} as Record<string, typeof cpses>)
                ).map(([sec, group]) => (
                  <optgroup key={sec} label={sec}>
                    {group.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.code} ({c.name})
                      </option>
                    ))}
                  </optgroup>
                ))
              ) : (
                <>
                  <optgroup label="Oil & Gas">
                    <option value="CPCL">CPCL (Chennai Petroleum Corporation Ltd)</option>
                    <option value="IOCL">IOCL (Indian Oil Corporation Ltd)</option>
                    <option value="BPCL">BPCL (Bharat Petroleum Corporation Ltd)</option>
                    <option value="ONGC">ONGC (Oil and Natural Gas Corp)</option>
                  </optgroup>
                  <optgroup label="Power & Steel & Mining">
                    <option value="NTPC">NTPC (Power Generation Ltd)</option>
                    <option value="SAIL">SAIL (Steel Authority of India Ltd)</option>
                    <option value="COALINDIA">Coal India (Mining & Minerals)</option>
                    <option value="BHEL">BHEL (Heavy Electricals Ltd)</option>
                  </optgroup>
                </>
              )}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="text-xs font-medium text-zinc-300 block mb-1.5">Extract File</label>
            <div className="flex items-center space-x-3">
              <input
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={handleFileChange}
                className="w-full text-xs text-zinc-400 file:mr-4 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-white file:text-black hover:file:bg-zinc-200 cursor-pointer glass-input rounded-xl"
              />
              {isDetecting && (
                <div className="flex items-center space-x-1.5 text-xs text-zinc-300 font-medium whitespace-nowrap">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Detecting...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Sample Selector */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-zinc-400">
          <span>Quick Sample:</span>
          <button
            type="button"
            onClick={() => loadSample("CPCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            CPCL (O&G)
          </button>
          <button
            type="button"
            onClick={() => loadSample("IOCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            IOCL (O&G)
          </button>
          <button
            type="button"
            onClick={() => loadSample("BPCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            BPCL (O&G)
          </button>
          <button
            type="button"
            onClick={() => loadSample("NTPC")}
            className="px-2.5 py-1 rounded-lg bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 border border-amber-500/20 apple-press font-medium"
          >
            NTPC (Power)
          </button>
          <button
            type="button"
            onClick={() => loadSample("SAIL")}
            className="px-2.5 py-1 rounded-lg bg-blue-950/40 hover:bg-blue-900/50 text-blue-300 border border-blue-500/20 apple-press font-medium"
          >
            SAIL (Steel)
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-xl flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Data Quality Overview Card */}
        {detectData?.quality_report && (
          <div className="p-4 bg-zinc-900/60 border border-white/[0.08] rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-200 flex items-center space-x-1.5">
                <FileCheck2 className="h-4 w-4 text-emerald-400" />
                <span>Pre-Flight Data Health Score</span>
              </span>
              <span className={`text-xs font-bold font-mono px-2.5 py-0.5 rounded-full ${
                (detectData.quality_score || 0) >= 0.85 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                  : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
              }`}>
                {Math.round((detectData.quality_score || 0) * 100)}% Quality
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-1 text-[11px] text-zinc-400">
              <div>Completeness: <span className="text-white font-mono">{Math.round((detectData.quality_report.completeness_rate || 1) * 100)}%</span></div>
              <div>Validity: <span className="text-white font-mono">{Math.round((detectData.quality_report.validity_rate || 1) * 100)}%</span></div>
              <div>Header Offset: <span className="text-white font-mono">Row #{detectData.header_row_index + 1}</span></div>
            </div>
          </div>
        )}

        {batchResult && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-xl flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
              <div>
                <span className="font-bold block text-emerald-200">
                  Batch Ingestion Completed Successfully
                </span>
                <span className="text-[11px] text-emerald-300/80">
                  Batch #{batchResult.id} for {batchResult.cpse_code} processed {batchResult.total_rows} records into active catalog.
                </span>
              </div>
            </div>
            <Link
              href="/materials"
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 rounded-lg text-xs font-semibold transition"
            >
              <span>View In Catalog</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>

      {/* Step 2: Column Mapping Profile */}
      {detectData && (
        <div className="glass-card rounded-2xl overflow-hidden space-y-4 p-6">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div>
              <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider block">
                Step 2 • Column Mapping Profile
              </span>
              <p className="text-xs text-zinc-400 mt-0.5">
                Headers automatically matched against CPSE engineering dictionary.
              </p>
            </div>
            <span className="text-xs text-zinc-300 font-mono px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/[0.08]">
              {detectData.file_name}
            </span>
          </div>

          {hasDuplicateTargets && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs rounded-xl flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-amber-400" />
              <span>Duplicate target field detected: <strong>{duplicateTargets.join(", ")}</strong>. Each field must map to only one source column.</span>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-300">
              <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                <tr>
                  <th className="py-3 px-4">Source Column ({selectedCPSE})</th>
                  <th className="py-3 px-4">Detected Field</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono">
                {detectData.detected_columns.map((col: string) => {
                  const target = mappingConfig[col] || "unmapped";
                  const conf = detectData.confidence_scores[col] || 0.90;
                  const isDuplicate = target !== "unmapped" && (targetCounts[target] || 0) > 1;
                  return (
                    <tr key={col} className={`hover:bg-zinc-900/40 transition-colors ${isDuplicate ? "bg-amber-500/[0.04]" : ""}`}>
                      <td className="py-3 px-4 font-semibold text-white">{col}</td>
                      <td className="py-3 px-4">
                        <select
                          value={target}
                          onChange={(e) => handleMappingChange(col, e.target.value)}
                          className={`glass-input rounded-lg px-3 py-1.5 text-xs font-sans focus:outline-none ${
                            isDuplicate ? "border-amber-500/50 text-amber-200" : "text-zinc-100"
                          }`}
                        >
                          <option value="material_code">material_code (Material / SAP Code)</option>
                          <option value="short_description">short_description (Specification Text)</option>
                          <option value="uom">uom (Unit of Measure)</option>
                          <option value="base_price">base_price (Last PO Unit Price)</option>
                          <option value="vendor_name">vendor_name (Manufacturer / Supplier)</option>
                          <option value="hsn_code">hsn_code (Tax / Tariff Code)</option>
                          <option value="unmapped">-- Unmapped / Ignore --</option>
                        </select>
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                          conf >= 0.90
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {Math.round(conf * 100)}% {conf >= 0.90 ? "High" : "Medium"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-sans">
                        {isDuplicate ? (
                          <span className="inline-flex items-center text-amber-400 text-xs font-medium">
                            <AlertCircle className="h-3.5 w-3.5 mr-1" /> Duplicate
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-zinc-300 text-xs font-medium">
                            <FileCheck2 className="h-3.5 w-3.5 mr-1 text-zinc-400" /> Auto-Validated
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Step 3: Live 5-Row Normalization Preview */}
          <div className="pt-5 border-t border-white/[0.08] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
                Step 3 • Live 5-Row Normalization Preview
              </span>
              <span className="text-[11px] text-zinc-500">
                Resolved text from: <strong className="text-zinc-300 font-mono">{descColumn || "unmapped"}</strong>
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Raw Description</th>
                    <th className="py-2.5 px-3">Preprocessed Text</th>
                    <th className="py-2.5 px-3">Extracted Attributes</th>
                    <th className="py-2.5 px-3">UOM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {detectData.preview_rows.map((row: any, idx: number) => {
                    const dynamicRawDesc = descColumn && row[descColumn] !== undefined && String(row[descColumn]).trim() !== "" 
                      ? String(row[descColumn]) 
                      : (row.ITEM_SPEC || row.DESCRIPTION || row.MAKTX || row.SHORT_DESC || Object.values(row)[1] || "");
                    const dynamicRawUom = uomColumn && row[uomColumn] !== undefined 
                      ? String(row[uomColumn]) 
                      : (row._preview_uom || "EA");

                    return (
                      <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                        <td className="py-3 px-3 font-mono text-zinc-500">{idx + 1}</td>
                        <td className="py-3 px-3 text-zinc-400 font-mono text-[11px]">
                          {dynamicRawDesc}
                        </td>
                        <td className="py-3 px-3 text-zinc-200 font-medium">
                          {row._preview_normalized_desc || dynamicRawDesc}
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex flex-wrap gap-1">
                            {row._preview_specs?.item_noun && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                                {row._preview_specs.item_noun}
                              </span>
                            )}
                            {row._preview_specs?.nominal_size && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                                {row._preview_specs.nominal_size}
                              </span>
                            )}
                            {row._preview_specs?.pressure_class && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                                {row._preview_specs.pressure_class}
                              </span>
                            )}
                            {row._preview_specs?.moc && (
                              <span className="px-2 py-0.5 bg-zinc-800 text-zinc-200 rounded-md text-[10px] border border-white/[0.06]">
                                {row._preview_specs.moc}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-3 font-bold text-white font-mono">{dynamicRawUom}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Live Progress Bar & Status */}
            {progressInfo && (
              <div className="p-4 bg-zinc-950/80 rounded-xl border border-white/[0.08] space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-zinc-200 flex items-center space-x-2">
                    {progressInfo.status === "PROCESSING" && (
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-amber-400 inline mr-1" />
                    )}
                    {progressInfo.status === "COMPLETED" && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 inline mr-1" />
                    )}
                    <span>Batch #{progressInfo.id} • {progressInfo.status}</span>
                  </span>
                  <span className="font-mono text-zinc-400">
                    {progressInfo.processed} / {progressInfo.total} rows ({progressInfo.percent}%)
                  </span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 rounded-full ${
                      progressInfo.status === "COMPLETED" ? "bg-emerald-500" : "bg-white"
                    }`}
                    style={{ width: `${Math.max(5, progressInfo.percent)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Action Bar & Mandatory Field Checklist */}
            <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center space-x-4 text-xs font-medium">
                <span className={`inline-flex items-center ${isMaterialCodeMapped ? "text-emerald-400" : "text-zinc-500"}`}>
                  <CheckCircle2 className={`h-3.5 w-3.5 mr-1 ${isMaterialCodeMapped ? "text-emerald-400" : "text-zinc-600"}`} />
                  Material Code {isMaterialCodeMapped ? "Mapped" : "Required"}
                </span>
                <span className={`inline-flex items-center ${isShortDescMapped ? "text-emerald-400" : "text-zinc-500"}`}>
                  <CheckCircle2 className={`h-3.5 w-3.5 mr-1 ${isShortDescMapped ? "text-emerald-400" : "text-zinc-600"}`} />
                  Description {isShortDescMapped ? "Mapped" : "Required"}
                </span>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleStartBatch}
                  disabled={isStartingBatch || !canStartBatch || (progressInfo?.status === "PROCESSING")}
                  className="flex items-center space-x-2 px-6 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  <span>{isStartingBatch ? "Processing Batch..." : "Start Batch Ingestion"}</span>
                  <ArrowRight className="h-4 w-4 text-black" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Recent Ingestion Batches Ledger */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="h-4 w-4 text-zinc-400" />
            <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
              Recent Ingestion Batches & Jobs
            </span>
          </div>
          <span className="text-[11px] text-zinc-500">{batches.length} total batches</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 font-medium border-b border-white/[0.08]">
              <tr>
                <th className="py-3 px-4">Batch ID</th>
                <th className="py-3 px-4">CPSE</th>
                <th className="py-3 px-4">File Name</th>
                <th className="py-3 px-4">Progress</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {batches.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-5 text-center text-zinc-500">
                    No ingestion batches recorded yet. Upload an extract or click a Quick Sample above.
                  </td>
                </tr>
              ) : (
                batches.map((b) => (
                  <tr key={b.id} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-white">#{b.id}</td>
                    <td className="py-3 px-4 font-semibold text-zinc-200">{b.cpse_code}</td>
                    <td className="py-3 px-4 font-mono text-zinc-300">{b.file_name}</td>
                    <td className="py-3 px-4 font-mono">
                      {b.processed_rows} / {b.total_rows} rows
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                        b.status === "COMPLETED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : b.status === "PROCESSING" || b.status === "PENDING"
                          ? "bg-sky-500/10 text-sky-400 border border-sky-500/20 inline-flex items-center space-x-1"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-500 font-mono text-[11px]">
                      {new Date(b.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
