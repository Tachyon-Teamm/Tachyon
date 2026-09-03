from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.core.database import get_sync_session
from app.services.export.sap_export import SAPExportService

router = APIRouter(prefix="/export", tags=["SAP LSMW / LTMC Export"])

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
