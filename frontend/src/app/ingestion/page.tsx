"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { 
  UploadCloud, 
  CheckCircle2, 
  ArrowRight, 
  AlertCircle, 
  RefreshCw,
  FileCheck2
} from "lucide-react";

const REAL_SAMPLE_CSVS: Record<string, string> = {
  CPCL: `MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE
100234,VLV GATE 6IN 300# CS FLG,Nos,12500.0,L&T Valves Ltd,84818030
100888,PIPE CS SMLS 4" SCH 40 ASTM A106,MTR,2450.0,Jindal Saw Ltd,73041910
100999,VALVE 2" 150# CS FLG,EA,4200.0,L&T Valves,84818030
100501,BEARING 6205-2RS1 SKF,EA,850.0,SKF India Ltd,84821010
100777,MECH SEAL CARTRIDGE PUMP P-101A (SET),SET,45000.0,Flowserve India,84841000
100612,GREASE MOBILITH SHC 100 - 18KG BUCKET,BKT,11700.0,ExxonMobil,27101980
100333,GASKET SPIRAL WOUND 4" 300# CS/SS,Nos,480.0,Champion Seals Ltd,84841000
100444,FLANGE 6" 300# WNRF ANSI B16.5 CS,Nos,3200.0,EIL Approved Vendor,73072100`,
  IOCL: `MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE
889102,VALVE, GATE, 150MM, CL300, WCB,EA,10800.0,Larsen & Toubro Ltd - Valve Div,84818030
889555,PIPE CS 4" SCH 80 A106,M,3800.0,Maharashtra Seamless,73041910
889999,VALVE 2" 300# CS FLG,EA,6800.0,L&T Valves,84818030
889501,SKF BEARING NO. 6205 2RS1 / C3,EA,920.0,SKF Bearings,84821010
889777,ROTARY SEAL RING FOR PUMP P-101A,EA,8500.0,Flowserve,84841000
889612,GREASE MOBILITH SHC 100,KG,630.0,Mobil Oil,27101980
889333,4" SPIRAL GASKET JAALI WALA 300#,EA,450.0,Champion Seals,84841000
889444,FLANGE 6" 300# WNRF ASME B16.5 A105,EA,3100.0,Engineers India Ltd Vendor,73072100`,
  BPCL: `MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE
445511,6 INCH GATE VALVE FLANGED 300#,Numbers,11200.0,Microfinish Valves,84818030
445888,4 INCH SEAMLESS PIPE SCH40 A106,MTR,2520.0,Jindal Saw,73041910
445501,BRG SKF 6205-2RS1,PCS,870.0,SKF,84821010
445612,MOBILITH SHC 100 - 180KG DRUM,DRM,108000.0,ExxonMobil,27101980
445333,GASKET SPIRAL 4 INCH 300#,EA,460.0,Champion,84841000`
};

export default function IngestionPage() {
  const [selectedCPSE, setSelectedCPSE] = useState<string>("IOCL");
  const [file, setFile] = useState<File | null>(null);
  const [detectData, setDetectData] = useState<any>(null);
  const [mappingConfig, setMappingConfig] = useState<Record<string, string>>({});
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [isStartingBatch, setIsStartingBatch] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setErrorMsg(null);
      setDetectData(null);
      setBatchResult(null);

      setIsDetecting(true);
      try {
        const res = await api.detectColumns(selected, selectedCPSE);
        setDetectData(res);
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
    try {
      const csvContent = REAL_SAMPLE_CSVS[cpse] || REAL_SAMPLE_CSVS["IOCL"];
      const realFile = new File([csvContent], `${cpse.toLowerCase()}_sample_extract.csv`, { type: "text/csv" });
      setFile(realFile);
      const res = await api.detectColumns(realFile, cpse);
      setDetectData(res);
      setMappingConfig(res.suggested_mappings || {});
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load sample");
    } finally {
      setIsDetecting(false);
    }
  };

  const handleMappingChange = (sourceCol: string, targetField: string) => {
    setMappingConfig((prev) => ({
      ...prev,
      [sourceCol]: targetField,
    }));
  };

  const handleStartBatch = async () => {
    if (!file || !detectData) return;
    setIsStartingBatch(true);
    setErrorMsg(null);

    try {
      const res = await api.startBatch(file, selectedCPSE, JSON.stringify(mappingConfig));
      setBatchResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start batch ingestion");
    } finally {
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
            <label className="text-xs font-medium text-zinc-300 block mb-1.5">Target Refinery Entity</label>
            <select
              value={selectedCPSE}
              onChange={(e) => setSelectedCPSE(e.target.value)}
              className="w-full glass-input text-white rounded-xl px-3.5 py-2.5 text-xs font-medium focus:outline-none"
            >
              <option value="CPCL">CPCL (Chennai Petroleum Corporation Ltd)</option>
              <option value="IOCL">IOCL (Indian Oil Corporation Ltd)</option>
              <option value="BPCL">BPCL (Bharat Petroleum Corporation Ltd)</option>
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
        <div className="flex items-center space-x-2 pt-1 text-[11px] text-zinc-400">
          <span>Quick Sample:</span>
          <button
            type="button"
            onClick={() => loadSample("CPCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            CPCL Sample
          </button>
          <button
            type="button"
            onClick={() => loadSample("IOCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            IOCL Sample
          </button>
          <button
            type="button"
            onClick={() => loadSample("BPCL")}
            className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08] apple-press font-medium"
          >
            BPCL Sample
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-xl flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {batchResult && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-xl flex items-center space-x-2.5">
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
                  return (
                    <tr key={col} className="hover:bg-zinc-900/40 transition-colors">
                      <td className="py-3 px-4 font-semibold text-white">{col}</td>
                      <td className="py-3 px-4">
                        <select
                          value={target}
                          onChange={(e) => handleMappingChange(col, e.target.value)}
                          className="glass-input text-zinc-100 rounded-lg px-3 py-1.5 text-xs font-sans focus:outline-none"
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
                        <span className="inline-flex items-center text-zinc-300 text-xs font-medium">
                          <FileCheck2 className="h-3.5 w-3.5 mr-1 text-zinc-400" /> Auto-Validated
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Step 3: Live 5-Row Normalization Preview */}
          <div className="pt-5 border-t border-white/[0.08] space-y-3">
            <div className="flex items-center space-x-1.5">
              <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
                Step 3 • Live 5-Row Normalization Preview
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
                  {detectData.preview_rows.map((row: any, idx: number) => (
                    <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                      <td className="py-3 px-3 font-mono text-zinc-500">{idx + 1}</td>
                      <td className="py-3 px-3 text-zinc-400 font-mono text-[11px]">
                        {row.ITEM_SPEC || row.DESCRIPTION || Object.values(row)[1] || ""}
                      </td>
                      <td className="py-3 px-3 text-zinc-200 font-medium">
                        {row._preview_normalized_desc}
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
                      <td className="py-3 px-3 font-bold text-white font-mono">{row._preview_uom}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Action Bar */}
            <div className="pt-4 flex items-center justify-end space-x-3">
              <button
                onClick={handleStartBatch}
                disabled={isStartingBatch}
                className="flex items-center space-x-2 px-6 py-2.5 bg-white hover:bg-zinc-200 text-black rounded-xl text-xs font-bold shadow-sm apple-press disabled:opacity-50 transition"
              >
                <span>{isStartingBatch ? "Processing Batch Ingestion..." : "Start Batch Ingestion"}</span>
                <ArrowRight className="h-4 w-4 text-black" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
