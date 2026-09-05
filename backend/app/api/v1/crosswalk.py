from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from app.core.database import get_sync_session
from app.models.models import CNMCCode, GoldenRecord
from app.schemas.schemas import CNMCDetailResponse, ReverseLookupResponse
from app.services.governance.crosswalk_service import CrosswalkService

router = APIRouter(prefix="/crosswalk", tags=["Unified Crosswalk Hub"])

@router.get("/registry", response_model=List[CNMCDetailResponse])
def list_cnmc_registry(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    sync_db = get_sync_session()
    try:
        cnmcs = sync_db.query(CNMCCode).join(GoldenRecord).offset(offset).limit(limit).all()
        out = []
        for c in cnmcs:
            detail = CrosswalkService.format_cnmc_detail(sync_db, c)
            if detail:
                out.append(detail)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch crosswalk registry: {str(e)}")
    finally:
        sync_db.close()

@router.get("/lookup", response_model=ReverseLookupResponse)
def reverse_lookup(
    local_code: str = Query(..., description="Local CPCL, IOCL, or BPCL material code, or National CNMC code"),
    cpse_code: Optional[str] = Query(None, description="CPCL, IOCL, or BPCL")
):
    cleaned_code = local_code.strip()
    if not cleaned_code:
        raise HTTPException(status_code=400, detail="Search query code cannot be empty.")

    sync_db = get_sync_session()
    try:
        details = CrosswalkService.reverse_lookup(sync_db, local_code=cleaned_code, cpse_code=cpse_code)
        if not details:
            return ReverseLookupResponse(
                query_code=cleaned_code,
                cpse_code=cpse_code or "ALL",
                found=False,
                cnmc_details=None
            )
        return ReverseLookupResponse(
            query_code=cleaned_code,
            cpse_code=cpse_code or "ALL",
            found=True,
            cnmc_details=details
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reverse lookup failed: {str(e)}")
    finally:
        sync_db.close()
