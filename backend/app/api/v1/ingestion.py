import os
import io
import re
import uuid
import glob
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, TokenData
from app.models.models import IngestionBatch, RawMaterial, CPSE, ColumnMapping
from app.schemas.schemas import ColumnMappingDetectResponse, IngestionBatchResponse, BatchProgressResponse
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.tasks.ingestion_tasks import process_ingestion_batch_task
from app.core.config import settings
from app.services.normalization.data_profiler import DataProfiler

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Normalization"])

UPLOAD_STAGING_DIR = os.path.join(os.getcwd(), "temp_uploads")
os.makedirs(UPLOAD_STAGING_DIR, exist_ok=True)

from pydantic import BaseModel

class PreviewRecalculateRequest(BaseModel):
    preview_rows: List[Dict[str, Any]]
    mapping_config: Dict[str, str]

# Expanded standard header patterns across Oil & Gas, Power, Steel, Mining, Heavy Eng
STANDARD_HEADER_SYNONYMS = {
    "material_code": [
        "MATERIAL_NO", "MATERIAL_CODE", "MATNR", "ITEM_CODE", "CODE", "MAT_CODE", 
        "SAP_CODE", "PART_NO", "ITEM_NO", "MAT_NO", "MATERIAL_NUMBER", "MATERIAL_ID", "ITEM_ID"
    ],
    "short_description": [
        "ITEM_SPEC", "DESCRIPTION", "SHORT_DESC", "MAKTX", "MATERIAL_DESC", "ITEM_DESCRIPTION", 
        "DESC", "SPECIFICATION", "ITEM_NAME", "SHORT_TEXT", "PURCHASING_TEXT", "MATERIAL_TEXT"
    ],
    "uom": [
        "UNIT_OF_MEASURE", "UOM", "MEINS", "UNIT", "BASE_UOM", "ORDER_UNIT", 
        "PURCHASE_ORDER_UNIT", "PO_UNIT", "BOM_UOM", "MEASURE_UNIT"
    ],
    "base_price": [
        "LAST_PO_PRICE", "PRICE", "NETPR", "UNIT_PRICE", "RATE", "LAST_PRICE", 
        "PO_RATE", "BASIC_PRICE", "NET_PRICE", "UNIT_RATE", "PO_PRICE", "STANDARD_PRICE"
    ],
    "vendor_name": [
        "VENDOR_NAME", "VENDOR", "NAME1", "SUPPLIER", "MANUFACTURER", "MFR", 
        "VENDOR_DESC", "SUPPLIER_NAME", "VENDOR_NAME_1", "MFG_NAME"
    ],
    "hsn_code": [
        "HSN_CODE", "HSN", "SAC", "TARIFF_CODE", "COMMODITY_CODE", "HSN_SAC", 
        "SAC_CODE", "TAX_CODE", "SAC_NO", "HSN_NO"
    ],
    "part_number": [
        "PART_NUMBER", "PART_NO", "CATALOG_NO", "OEM_PART_NO", "MODEL_NO", "CAT_NO"
    ],
    "voltage_rating": [
        "VOLTAGE", "VOLTS", "RATED_VOLTAGE", "VOLTAGE_RATING", "KV", "VOLT_RATING"
    ],
    "current_rating": [
        "CURRENT", "AMPS", "RATED_CURRENT", "CURRENT_RATING", "AMPERES", "AMP_RATING"
    ]
}

def read_dataframe_resilient(file_path: str, header_idx: int = 0, nrows: Optional[int] = None) -> pd.DataFrame:
    """
    Resilient DataFrame reader supporting multi-encoding cascade (utf-8-sig, utf-8, cp1252, latin1),
    delimiter sniffing (,, ;, \t, |), and BOM stripping.
    """
    if file_path.endswith((".xls", ".xlsx")):
        df = pd.read_excel(file_path, header=header_idx, nrows=nrows)
        df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
        return df

    encodings = ["utf-8-sig", "utf-8", "cp1252", "iso-8859-1"]
    last_err = None

    for enc in encodings:
        try:
            df = pd.read_csv(
                file_path,
                header=header_idx,
                nrows=nrows,
                encoding=enc,
                sep=None,
                engine="python"
            )
            df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
            return df
        except Exception as e:
            last_err = e
            try:
                df = pd.read_csv(
                    file_path,
                    header=header_idx,
                    nrows=nrows,
                    encoding=enc,
                    sep=","
                )
                df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
                return df
            except Exception:
                continue

    raise ValueError(f"Failed to parse CSV with supported encodings: {last_err}")

@router.post("/detect-columns", response_model=ColumnMappingDetectResponse)
async def detect_columns(
    file: UploadFile = File(...),
    cpse_code: str = Form("IOCL")
):
    try:
        # Stage file for single-upload Claim-Check Pattern using chunked streaming
        upload_id = uuid.uuid4().hex
        safe_filename = "".join(c for c in (file.filename or "upload.csv") if c.isalnum() or c in "._-")
        staged_path = os.path.join(UPLOAD_STAGING_DIR, f"{upload_id}_{safe_filename}")
        
        with open(staged_path, "wb") as f_out:
            while chunk := await file.read(65536):
                f_out.write(chunk)

        # Smart Header Offset Auto-Detector (scans first 5 rows)
        best_df = None
        best_header_idx = 0
        max_matches = -1

        for header_idx in range(5):
            try:
                temp_df = read_dataframe_resilient(staged_path, header_idx=header_idx, nrows=15)
                cols = [str(c).strip().upper() for c in temp_df.columns if not str(c).startswith("Unnamed")]
                matches = 0
                for c in cols:
                    c_clean = re.sub(r'[^A-Z0-9]', '_', c).strip('_')
                    for synonyms in STANDARD_HEADER_SYNONYMS.values():
                        if any(re.search(r'\b' + re.escape(syn) + r'\b', c) or syn == c_clean for syn in synonyms):
                            matches += 1
                            break
                if matches > max_matches:
                    max_matches = matches
                    best_df = temp_df
                    best_header_idx = header_idx
            except Exception:
                continue

        df = best_df if best_df is not None else read_dataframe_resilient(staged_path, header_idx=0, nrows=15)
            
        columns = [str(c) for c in df.columns]
        suggested: Dict[str, str] = {}
        confidences: Dict[str, float] = {}

        # Pass 1: Strict Exact Match across all categories
        for col in columns:
            col_clean = re.sub(r'[^A-Z0-9]', '_', str(col).strip().upper())
            col_clean = re.sub(r'_+', '_', col_clean).strip('_')
            matched = False
            for target_field, synonyms in STANDARD_HEADER_SYNONYMS.items():
                for syn in synonyms:
                    syn_clean = re.sub(r'[^A-Z0-9]', '_', syn.upper()).strip('_')
                    if col_clean == syn_clean or str(col).strip().upper() == syn:
                        suggested[col] = target_field
                        confidences[col] = 0.98
                        matched = True
                        break
                if matched:
                    break

        # Pass 2: Boundary-Aware Regex Disambiguation for remaining columns
        # Check specific compounds first (hsn_code, base_price, vendor_name) before generic material_code/uom
        category_order = ["hsn_code", "base_price", "vendor_name", "short_description", "uom", "material_code"]
        for col in columns:
            if col in suggested:
                continue
            col_upper = str(col).strip().upper()
            matched = False
            for target_field in category_order:
                synonyms = STANDARD_HEADER_SYNONYMS[target_field]
                for syn in synonyms:
                    pattern = r'\b' + re.escape(syn.upper()) + r'\b'
                    if re.search(pattern, col_upper):
                        suggested[col] = target_field
                        confidences[col] = 0.90
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                suggested[col] = "unmapped"
                confidences[col] = 0.50

        # Generate 5-row live preview with bulkhead per-row fault isolation
        preview_data = []
        raw_rows_for_profiler = []
        for idx, row in df.head(5).iterrows():
            desc_val = ""
            for c, t in suggested.items():
                if t == "short_description" and c in row:
                    val = row[c]
                    desc_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else ""
                    break
            
            uom_val = "EA"
            for c, t in suggested.items():
                if t == "uom" and c in row:
                    val = row[c]
                    uom_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else "EA"
                    break

            code_val = ""
            for c, t in suggested.items():
                if t == "material_code" and c in row:
                    val = row[c]
                    code_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else ""
                    break
                    
            try:
                multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc_val, uom_val)
                specs = SpecExtractor.extract_specs(desc_val)
            except Exception:
                multiplier, base_uom = 1.0, UOMNormalizer.normalize_uom(uom_val)
                specs = {"raw_preprocessed": desc_val, "item_noun": None}
            
            row_dict = row.fillna("").to_dict()
            row_dict["_preview_normalized_desc"] = specs.get("raw_preprocessed") or desc_val
            row_dict["_preview_uom"] = UOMNormalizer.normalize_uom(uom_val)
            row_dict["_preview_specs"] = specs
            preview_data.append(row_dict)
            raw_rows_for_profiler.append({
                "material_code": code_val,
                "short_description": desc_val,
                "uom": uom_val
            })

        # Profile Data Quality
        quality_report = DataProfiler.profile_records(raw_rows_for_profiler)

        return ColumnMappingDetectResponse(
            file_name=file.filename,
            upload_id=upload_id,
            detected_columns=columns,
            suggested_mappings=suggested,
            confidence_scores=confidences,
            preview_rows=preview_data,
            header_row_index=best_header_idx,
            quality_score=quality_report.quality_score,
            quality_report=quality_report.to_dict()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(e)}")

@router.post("/start-batch", response_model=IngestionBatchResponse)
async def start_batch(
    background_tasks: BackgroundTasks,
    upload_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    cpse_code: str = Form("IOCL"),
    mapping_config_json: str = Form(...),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    import json
    try:
        mapping_dict = json.loads(mapping_config_json)
        
        # Resolve CPSE
        cpse_res = await db.execute(select(CPSE).filter(CPSE.code == cpse_code.upper()))
        cpse = cpse_res.scalars().first()
        if not cpse:
            raise HTTPException(status_code=404, detail=f"CPSE {cpse_code} not found")

        staged_file_path = None
        file_name = "upload.csv"
        file_size_bytes = 0

        # 1. Resolve source file (staged upload_id or direct upload)
        if upload_id:
            pattern = os.path.join(UPLOAD_STAGING_DIR, f"{upload_id}_*")
            matching_files = glob.glob(pattern)
            if matching_files:
                staged_file_path = matching_files[0]
                file_name = os.path.basename(staged_file_path).replace(f"{upload_id}_", "")
                file_size_bytes = os.path.getsize(staged_file_path)
        
        if not staged_file_path and file:
            file_name = file.filename or "upload.csv"
            direct_id = uuid.uuid4().hex
            safe_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
            staged_file_path = os.path.join(UPLOAD_STAGING_DIR, f"direct_{direct_id}_{safe_name}")
            with open(staged_file_path, "wb") as f_out:
                while chunk := await file.read(65536):
                    f_out.write(chunk)
            file_size_bytes = os.path.getsize(staged_file_path) if os.path.exists(staged_file_path) else 0

        if not staged_file_path or not os.path.exists(staged_file_path):
            raise HTTPException(status_code=400, detail="No file found for ingestion batch. Please upload a file.")

        # 2. Validation Gate: Ensure 1:1 target mapping and mandatory fields
        active_mappings = {k: v for k, v in mapping_dict.items() if v != "unmapped"}
        target_counts: Dict[str, List[str]] = {}
        for source_col, target_field in active_mappings.items():
            target_counts.setdefault(target_field, []).append(source_col)

        duplicates = {t: cols for t, cols in target_counts.items() if len(cols) > 1}
        if duplicates:
            dup_details = ", ".join([f"'{t}' mapped to {cols}" for t, cols in duplicates.items()])
            raise HTTPException(
                status_code=400, 
                detail=f"Mapping validation failed: duplicate target assignments detected ({dup_details}). Each target field must map to only one source column."
            )

        if "material_code" not in target_counts:
            raise HTTPException(
                status_code=400,
                detail="Mapping validation failed: 'material_code' is mandatory but unmapped."
            )
        if "short_description" not in target_counts:
            raise HTTPException(
                status_code=400,
                detail="Mapping validation failed: 'short_description' is mandatory but unmapped."
            )

        # 3. Count total rows and stream into Bronze layer using resilient reader
        full_df = read_dataframe_resilient(staged_file_path)
        total_rows = len(full_df)

        # Create Ingestion Batch in database
        batch = IngestionBatch(
            cpse_id=cpse.id,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            total_rows=total_rows,
            processed_rows=0,
            status="PROCESSING"
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        # 4. Stream raw records in memory-safe chunks of 2,000
        chunk_size = 2000
        for start_idx in range(0, total_rows, chunk_size):
            chunk_df = full_df.iloc[start_idx : start_idx + chunk_size]
            records = chunk_df.fillna("").to_dict(orient="records")
            raw_objs = [
                RawMaterial(
                    batch_id=batch.id,
                    cpse_id=cpse.id,
                    row_index=start_idx + i,
                    raw_data=row
                )
                for i, row in enumerate(records)
            ]
            db.add_all(raw_objs)
            await db.commit()

        # Clean up temporary staged file
        try:
            if os.path.exists(staged_file_path):
                os.remove(staged_file_path)
        except Exception:
            pass

        # Invert mapping: standard target -> source column
        inv_map = {v: k for k, v in active_mappings.items()}

        # 5. Asynchronous Task Dispatch with graceful Celery -> BackgroundTasks fallback
        try:
            process_ingestion_batch_task.delay(batch.id, inv_map)
        except Exception as celery_err:
            print(f"[Ingestion] Celery dispatch unavailable ({celery_err}), using FastAPI BackgroundTasks")
            background_tasks.add_task(process_ingestion_batch_task, batch.id, inv_map)

        return IngestionBatchResponse(
            id=batch.id,
            cpse_id=cpse.id,
            cpse_code=cpse.code,
            file_name=batch.file_name,
            total_rows=batch.total_rows,
            processed_rows=0,
            status="PROCESSING",
            created_at=batch.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch failed: {str(e)}")

@router.get("/batch/{batch_id}/status", response_model=BatchProgressResponse)
@router.get("/batches/{batch_id}/progress", response_model=BatchProgressResponse)
async def get_batch_status(batch_id: int, db: Session = Depends(get_db)):
    res = await db.execute(select(IngestionBatch).filter(IngestionBatch.id == batch_id))
    batch = res.scalars().first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    pct = round((batch.processed_rows / batch.total_rows * 100.0), 1) if (batch.total_rows and batch.total_rows > 0) else 0.0
    return BatchProgressResponse(
        id=batch.id,
        status=batch.status,
        total_rows=batch.total_rows,
        processed_rows=batch.processed_rows,
        percent_complete=min(100.0, pct),
        quality_score=getattr(batch, "quality_score", 1.0),
        error_message=getattr(batch, "error_message", None)
    )

@router.get("/batches", response_model=List[IngestionBatchResponse])
async def list_batches(db: Session = Depends(get_db)):
    res = await db.execute(select(IngestionBatch).order_by(IngestionBatch.created_at.desc()))
    batches = res.scalars().all()
    out = []
    for b in batches:
        cpse_res = await db.execute(select(CPSE).filter(CPSE.id == b.cpse_id))
        cpse = cpse_res.scalars().first()
        out.append(IngestionBatchResponse(
            id=b.id,
            cpse_id=b.cpse_id,
            cpse_code=cpse.code if cpse else "UNK",
            file_name=b.file_name,
            total_rows=b.total_rows,
            processed_rows=b.processed_rows,
            status=b.status,
            created_at=b.created_at
        ))
    return out

@router.get("/samples")
async def list_sample_datasets():
    """
    Returns available multi-sector ERP sample datasets across Oil & Gas, Power, and Steel.
    """
    samples = {
        "CPCL": {
            "sector": "OIL_AND_GAS",
            "name": "Chennai Petroleum Corporation Limited",
            "filename": "cpcl_sample_extract.csv",
            "content": (
                "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
                "100234,VLV GATE 6IN 300# CS FLG,Nos,12500.0,L&T Valves Ltd,84818030\n"
                "100888,PIPE CS SMLS 4\" SCH 40 ASTM A106,MTR,2450.0,Jindal Saw Ltd,73041910\n"
                "100999,VALVE 2\" 150# CS FLG,EA,4200.0,L&T Valves,84818030\n"
                "100501,BEARING 6205-2RS1 SKF,EA,850.0,SKF India Ltd,84821010\n"
                "100777,MECH SEAL CARTRIDGE PUMP P-101A (SET),SET,45000.0,Flowserve India,84841000\n"
                "100612,GREASE MOBILITH SHC 100 - 18KG BUCKET,BKT,11700.0,ExxonMobil,27101980\n"
                "100333,GASKET SPIRAL WOUND 4\" 300# CS/SS,Nos,480.0,Champion Seals Ltd,84841000\n"
                "100444,FLANGE 6\" 300# WNRF ANSI B16.5 CS,Nos,3200.0,EIL Approved Vendor,73072100"
            )
        },
        "IOCL": {
            "sector": "OIL_AND_GAS",
            "name": "Indian Oil Corporation Limited",
            "filename": "iocl_sample_extract.csv",
            "content": (
                "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
                "889102,VALVE, GATE, 150MM, CL300, WCB,EA,10800.0,Larsen & Toubro Ltd - Valve Div,84818030\n"
                "889555,PIPE CS 4\" SCH 80 A106,M,3800.0,Maharashtra Seamless,73041910\n"
                "889999,VALVE 2\" 300# CS FLG,EA,6800.0,L&T Valves,84818030\n"
                "889501,SKF BEARING NO. 6205 2RS1 / C3,EA,920.0,SKF Bearings,84821010\n"
                "889777,ROTARY SEAL RING FOR PUMP P-101A,EA,8500.0,Flowserve,84841000\n"
                "889612,GREASE MOBILITH SHC 100,KG,630.0,Mobil Oil,27101980\n"
                "889333,4\" SPIRAL GASKET JAALI WALA 300#,EA,450.0,Champion Seals,84841000\n"
                "889444,FLANGE 6\" 300# WNRF ASME B16.5 A105,EA,3100.0,Engineers India Ltd Vendor,73072100"
            )
        },
        "BPCL": {
            "sector": "OIL_AND_GAS",
            "name": "Bharat Petroleum Corporation Limited",
            "filename": "bpcl_sample_extract.csv",
            "content": (
                "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
                "445511,6 INCH GATE VALVE FLANGED 300#,Numbers,11200.0,Microfinish Valves,84818030\n"
                "445888,4 INCH SEAMLESS PIPE SCH40 A106,MTR,2520.0,Jindal Saw,73041910\n"
                "445501,BRG SKF 6205-2RS1,PCS,870.0,SKF,84821010\n"
                "445612,MOBILITH SHC 100 - 180KG DRUM,DRM,108000.0,ExxonMobil,27101980\n"
                "445333,GASKET SPIRAL 4 INCH 300#,EA,460.0,Champion,84841000"
            )
        },
        "NTPC": {
            "sector": "POWER",
            "name": "NTPC Limited (Power)",
            "filename": "ntpc_sample_extract.csv",
            "content": (
                "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
                "770101,TRANSFORMER 33KV / 11KV 10MVA ONAN,EA,4200000.0,BHEL,85042300\n"
                "770202,HT XLPE CABLE 3 CORE 11KV 300 SQMM,MTR,1850.0,Polycab India,85446090\n"
                "770303,VACUUM CIRCUIT BREAKER 11KV 1250A 25KA,EA,310000.0,ABB India,85352190"
            )
        },
        "SAIL": {
            "sector": "STEEL",
            "name": "Steel Authority of India Limited",
            "filename": "sail_sample_extract.csv",
            "content": (
                "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
                "990101,TMT REBAR FE 500D 16MM DIA IS 1786,MT,54000.0,SAIL Plants,72142090\n"
                "990202,HIGH ALUMINA REFRACTORY BRICK 70% AL2O3,MT,32000.0,TRL Krosaki,69022020\n"
                "990303,CONVEYOR BELTING 1200MM WIDTH 1000/4 GRADE M,MTR,4500.0,Fenner India,40101200"
            )
        }
    }
    return samples

@router.post("/preview")
async def recalculate_preview(req: PreviewRecalculateRequest):
    """
    Dynamically recalculates normalization and specification extraction
    on preview rows when user alters column mapping.
    """
    updated_preview = []
    raw_rows_for_profiler = []
    
    for row in req.preview_rows:
        desc_val = ""
        uom_val = "EA"
        code_val = ""
        
        for c, t in req.mapping_config.items():
            if t == "short_description" and c in row:
                val = row[c]
                desc_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else ""
            elif t == "uom" and c in row:
                val = row[c]
                uom_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else "EA"
            elif t == "material_code" and c in row:
                val = row[c]
                code_val = str(val).strip() if (pd.notna(val) and str(val).lower() != "nan") else ""

        try:
            multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc_val, uom_val)
            specs = SpecExtractor.extract_specs(desc_val)
        except Exception:
            multiplier, base_uom = 1.0, UOMNormalizer.normalize_uom(uom_val)
            specs = {"raw_preprocessed": desc_val, "item_noun": None}

        row_dict = dict(row)
        row_dict["_preview_normalized_desc"] = specs.get("raw_preprocessed") or desc_val
        row_dict["_preview_uom"] = UOMNormalizer.normalize_uom(uom_val)
        row_dict["_preview_specs"] = specs
        updated_preview.append(row_dict)
        raw_rows_for_profiler.append({
            "material_code": code_val,
            "short_description": desc_val,
            "uom": uom_val
        })

    quality_report = DataProfiler.profile_records(raw_rows_for_profiler)
    return {
        "preview_rows": updated_preview,
        "quality_score": quality_report.quality_score,
        "quality_report": quality_report.to_dict()
    }
