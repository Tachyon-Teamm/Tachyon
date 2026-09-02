from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import get_sync_db
from app.services.export.sap_export import SAPExportService

router = APIRouter(prefix="/export", tags=["SAP LSMW / LTMC Export"])

@router.get("/sap-lsmw-csv")
async def export_sap_lsmw_csv(
    cpse_code: Optional[str] = Query(None, description="Filter by CPSE code (e.g. CPCL, IOCL, BPCL, NTPC, ONGC, SAIL)")
):
    db = next(get_sync_db())
    try:
        csv_content = SAPExportService.generate_lsmw_csv(db, cpse_code=cpse_code)
        filename = f"SAP_LSMW_CNMC_{cpse_code or 'NATIONAL'}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        db.close()
