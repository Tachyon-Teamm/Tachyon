import os
import io
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, TokenData
from app.models.models import IngestionBatch, RawMaterial, CPSE, ColumnMapping
from app.schemas.schemas import ColumnMappingDetectResponse, IngestionBatchResponse
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.tasks.ingestion_tasks import process_ingestion_batch_task
from app.core.config import settings

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Normalization"])

from app.services.normalization.data_profiler import DataProfiler

# Known standard header patterns across Oil & Gas, Power, Steel, Mining, Heavy Eng
STANDARD_HEADER_SYNONYMS = {
    "material_code": ["MATERIAL_NO", "MATERIAL_CODE", "MATNR", "ITEM_CODE", "CODE", "MAT_CODE", "SAP_CODE", "PART_NO", "ITEM_NO", "MAT_NO"],
    "short_description": ["ITEM_SPEC", "DESCRIPTION", "SHORT_DESC", "MAKTX", "MATERIAL_DESC", "ITEM_DESCRIPTION", "DESC", "SPECIFICATION", "ITEM_NAME"],
    "uom": ["UNIT_OF_MEASURE", "UOM", "MEINS", "UNIT", "BASE_UOM", "ORDER_UNIT"],
    "base_price": ["LAST_PO_PRICE", "PRICE", "NETPR", "UNIT_PRICE", "RATE", "LAST_PRICE", "PO_RATE", "BASIC_PRICE"],
    "vendor_name": ["VENDOR_NAME", "VENDOR", "NAME1", "SUPPLIER", "MANUFACTURER", "MFR", "VENDOR_DESC"],
    "hsn_code": ["HSN_CODE", "HSN", "SAC", "TARIFF_CODE", "COMMODITY_CODE"]
}

@router.post("/detect-columns", response_model=ColumnMappingDetectResponse)
async def detect_columns(
    file: UploadFile = File(...),
    cpse_code: str = Form("IOCL")
):
    try:
        contents = await file.read()
        
        # Smart Header Offset Auto-Detector (scans first 5 rows)
        best_df = None
        best_header_idx = 0
        max_matches = -1

        for header_idx in range(5):
            try:
                if file.filename.endswith(".csv"):
                    temp_df = pd.read_csv(io.BytesIO(contents), header=header_idx, nrows=15)
                elif file.filename.endswith((".xls", ".xlsx")):
                    temp_df = pd.read_excel(io.BytesIO(contents), header=header_idx, nrows=15)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel.")

                cols = [str(c).strip().upper() for c in temp_df.columns if not str(c).startswith("Unnamed")]
                # Count matches against known synonyms
                matches = 0
                for c in cols:
                    for synonyms in STANDARD_HEADER_SYNONYMS.values():
                        if any(syn in c for syn in synonyms):
                            matches += 1
                            break
                if matches > max_matches:
                    max_matches = matches
                    best_df = temp_df
                    best_header_idx = header_idx
            except Exception:
                continue

        df = best_df if best_df is not None else pd.read_csv(io.BytesIO(contents), nrows=15)
            
        columns = [str(c) for c in df.columns]
        suggested: Dict[str, str] = {}
        confidences: Dict[str, float] = {}

        for col in columns:
            col_upper = str(col).strip().upper()
            matched = False
            for target_field, synonyms in STANDARD_HEADER_SYNONYMS.items():
                if col_upper in synonyms:
                    suggested[col] = target_field
                    confidences[col] = 0.98
                    matched = True
                    break
                elif any(syn in col_upper for syn in synonyms):
                    suggested[col] = target_field
                    confidences[col] = 0.90
                    matched = True
                    break
            if not matched:
                suggested[col] = "unmapped"
                confidences[col] = 0.50

        # Generate 5-row live preview with normalization
        preview_data = []
        raw_rows_for_profiler = []
        for idx, row in df.head(5).iterrows():
            desc_val = ""
            for c, t in suggested.items():
                if t == "short_description":
                    desc_val = str(row[c]) if pd.notna(row[c]) else ""
                    break
            
            uom_val = "EA"
            for c, t in suggested.items():
                if t == "uom":
                    uom_val = str(row[c]) if pd.notna(row[c]) else "EA"
                    break

            code_val = ""
            for c, t in suggested.items():
                if t == "material_code":
                    code_val = str(row[c]) if pd.notna(row[c]) else ""
                    break
                    
            multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc_val, uom_val)
            specs = SpecExtractor.extract_specs(desc_val)
            
            row_dict = row.fillna("").to_dict()
            row_dict["_preview_normalized_desc"] = specs.get("raw_preprocessed")
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
    file: UploadFile = File(...),
    cpse_code: str = Form("IOCL"),
    mapping_config_json: str = Form(...), # JSON string of mappings
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

        contents = await file.read()
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))

        # Create Ingestion Batch
        batch = IngestionBatch(
            cpse_id=cpse.id,
            file_name=file.filename,
            file_size_bytes=len(contents),
            total_rows=len(df),
            processed_rows=0,
            status="PENDING"
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        # Store raw records
        raw_objs = []
        for idx, row in df.iterrows():
            raw_objs.append(RawMaterial(
                batch_id=batch.id,
                cpse_id=cpse.id,
                row_index=idx,
                raw_data=row.fillna("").to_dict()
            ))
        db.add_all(raw_objs)
        await db.commit()

        # Invert mapping so standard target -> source column
        # e.g. mapping_dict is { "MATERIAL_NO": "material_code" }
        inv_map = {v: k for k, v in mapping_dict.items() if v != "unmapped"}

        # Run ingestion task
        try:
            from app.tasks.ingestion_tasks import process_ingestion_batch_task
            process_ingestion_batch_task(batch.id, inv_map)
            batch.status = "COMPLETED"
            batch.processed_rows = len(df)
            await db.commit()
        except Exception as task_err:
            batch.status = "FAILED"
            await db.commit()
            print(f"[Ingestion] Background task error: {task_err}")
            raise HTTPException(status_code=500, detail=f"Batch processing error: {str(task_err)}")

        return IngestionBatchResponse(
            id=batch.id,
            cpse_id=cpse.id,
            cpse_code=cpse.code,
            file_name=batch.file_name,
            total_rows=batch.total_rows,
            processed_rows=batch.processed_rows,
            status=batch.status,
            created_at=batch.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch failed: {str(e)}")

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
