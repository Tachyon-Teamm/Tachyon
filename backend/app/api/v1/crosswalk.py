from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db, get_sync_db
from app.models.models import CNMCCode, Crosswalk, GoldenRecord, Material, CPSE
from app.schemas.schemas import CNMCDetailResponse, ReverseLookupResponse
from app.services.governance.crosswalk_service import CrosswalkService

router = APIRouter(prefix="/crosswalk", tags=["Unified Crosswalk Hub"])

@router.get("/registry", response_model=List[CNMCDetailResponse])
async def list_cnmc_registry(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    sync_db = next(get_sync_db())
    try:
        cnmcs = sync_db.query(CNMCCode).join(GoldenRecord).offset(offset).limit(limit).all()
        out = []
        for c in cnmcs:
            detail = CrosswalkService.format_cnmc_detail(sync_db, c)
            if detail:
                out.append(detail)
        return out
    finally:
        sync_db.close()

@router.get("/lookup", response_model=ReverseLookupResponse)
async def reverse_lookup(
    local_code: str = Query(..., description="Local CPCL, IOCL, or BPCL material code"),
    cpse_code: Optional[str] = Query(None, description="CPCL, IOCL, or BPCL"),
    db: Session = Depends(get_db)
):
    sync_db = next(get_sync_db())
    try:
        details = CrosswalkService.reverse_lookup(sync_db, local_code=local_code.strip(), cpse_code=cpse_code)
        if not details:
            return ReverseLookupResponse(
                query_code=local_code,
                cpse_code=cpse_code or "ALL",
                found=False,
                cnmc_details=None
            )
        return ReverseLookupResponse(
            query_code=local_code,
            cpse_code=cpse_code or "ALL",
            found=True,
            cnmc_details=details
        )
    finally:
        sync_db.close()
