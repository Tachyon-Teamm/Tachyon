from typing import Optional
import os
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from app.core.database import get_sync_session
from app.services.export.sap_export import SAPExportService

router = APIRouter(prefix="/export", tags=["SAP LSMW / LTMC Export"])

def _resolve_dataset_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / "data" / "synthetic_datasets",
        Path(__file__).resolve().parents[4] / "data" / "synthetic_datasets",
        Path(__file__).resolve().parents[2] / "data" / "synthetic_datasets",
        Path("/app/data/synthetic_datasets"),
        Path(os.getcwd()) / "data" / "synthetic_datasets",
        Path(os.getcwd()) / "backend" / "data" / "synthetic_datasets",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

DATASET_DIR = _resolve_dataset_dir()

@router.get("/sap-lsmw-csv")
def export_sap_lsmw_csv(
    cpse_code: Optional[str] = Query(None, description="Filter by CPSE code (e.g. CPCL, IOCL, BPCL, NTPC, ONGC, SAIL)")
):
    """
    Streams SAP LSMW / LTMC compliant CSV material master migration data chunk-by-chunk.
    Prevents memory spikes on massive datasets.
    """
    def csv_stream_generator():
        db = get_sync_session()
        try:
            for chunk in SAPExportService.generate_lsmw_csv_stream(db, cpse_code=cpse_code):
                yield chunk
        finally:
            db.close()

    filename = f"SAP_LSMW_CNMC_{cpse_code or 'NATIONAL'}.csv"
    return StreamingResponse(
        csv_stream_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/synthetic-datasets/{filename}")
def download_synthetic_dataset(filename: str):
    """
    Direct download endpoint for CPSE synthetic benchmark CSV files.
    """
    safe_filename = os.path.basename(filename)
    file_path = DATASET_DIR / safe_filename
    if not file_path.exists() or not safe_filename.endswith((".csv", ".zip")):
        raise HTTPException(status_code=404, detail=f"Dataset file '{safe_filename}' not found.")
    media_type = "application/zip" if safe_filename.endswith(".zip") else "text/csv"
    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=safe_filename,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )

@router.get("/synthetic-datasets-zip")
def download_all_synthetic_datasets_zip():
    """
    Direct download of all CPSE synthetic benchmark datasets bundled in a single ZIP archive.
    """
    zip_path = DATASET_DIR / "unimm_all_synthetic_cpse_datasets.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Synthetic datasets archive not found.")
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="unimm_all_synthetic_cpse_datasets.zip",
        headers={"Content-Disposition": 'attachment; filename="unimm_all_synthetic_cpse_datasets.zip"'}
    )

