import os
from pathlib import Path
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
from app.schemas.schemas import ColumnMappingDetectResponse, IngestionBatchResponse, BatchProgressResponse, CPSEResponse
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.tasks.ingestion_tasks import process_ingestion_batch_task
from app.services.normalization.data_profiler import DataProfiler

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Normalization"])

@router.get("/cpses", response_model=List[CPSEResponse])
async def list_cpses(db: Session = Depends(get_db)):
    """Dynamically return all active CPSEs with sectors for entity selection."""
    res = await db.execute(select(CPSE).filter(CPSE.is_active == True).order_by(CPSE.sector.asc(), CPSE.code.asc()))
    return res.scalars().all()

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
    "quantity": [
        "QUANTITY", "QTY", "PO_QTY", "ANNUAL_DEMAND", "MENGE", "ORDER_QTY", "REQ_QTY", "DEMAND"
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
    header_row_index: Optional[int] = Form(0),
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
        header_idx = header_row_index if header_row_index is not None else 0
        full_df = read_dataframe_resilient(staged_file_path, header_idx=header_idx)
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
            quality_score=getattr(b, "quality_score", 1.0),
            created_at=b.created_at
        ))
    return out

@router.get("/samples")
async def list_sample_datasets():
    """
    Returns available multi-sector ERP sample datasets across Oil & Gas, Power, Steel, Mining, Heavy Eng.
    """
    root_data = Path(__file__).resolve().parents[4] / "data" / "synthetic_datasets"
    cwd_data = Path(os.getcwd()) / "data" / "synthetic_datasets"
    sample_dir = str(root_data if root_data.exists() else cwd_data)
    cpse_meta = {
        "CPCL": {"sector": "OIL_AND_GAS", "name": "Chennai Petroleum Corporation Limited", "file": "cpcl_materials.csv"},
        "IOCL": {"sector": "OIL_AND_GAS", "name": "Indian Oil Corporation Limited", "file": "iocl_materials.csv"},
        "BPCL": {"sector": "OIL_AND_GAS", "name": "Bharat Petroleum Corporation Limited", "file": "bpcl_materials.csv"},
        "ONGC": {"sector": "OIL_AND_GAS", "name": "Oil and Natural Gas Corporation", "file": "ongc_materials.csv"},
        "NTPC": {"sector": "POWER", "name": "NTPC Limited (Power)", "file": "ntpc_materials.csv"},
        "SAIL": {"sector": "STEEL", "name": "Steel Authority of India Limited", "file": "sail_materials.csv"},
        "BHEL": {"sector": "HEAVY_ENG", "name": "Bharat Heavy Electricals Limited", "file": "bhel_materials.csv"},
        "COALINDIA": {"sector": "MINING", "name": "Coal India Limited", "file": "coalindia_materials.csv"},
    }
    samples = {}
    for code, meta in cpse_meta.items():
        fpath = os.path.join(sample_dir, meta["file"])
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            samples[code] = {
                "sector": meta["sector"],
                "name": meta["name"],
                "filename": meta["file"],
                "content": content
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
