from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy import desc
from app.core.database import get_sync_session
from app.models.models import AuditLog
from app.schemas.schemas import AuditLogResponse, AuditVerifyResponse
from app.services.governance.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit & Compliance"])

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by action name e.g. REVIEW_APPROVAL, CNMC_MINTED"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type e.g. CNMC_CODE, REVIEW_QUEUE")
):
    """
    Returns immutable audit log records with SHA-256 HMAC cryptographic signatures.
    Complies with Government and CERT-In compliance requirements.
    """
    sync_db = get_sync_session()
    try:
        query = sync_db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action.upper())
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type.upper())

        logs = query.order_by(desc(AuditLog.id)).offset(offset).limit(limit).all()
        return [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                evidence=log.evidence or {},
                created_at=log.created_at
            )
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit logs: {str(e)}")
    finally:
        sync_db.close()

@router.get("/verify-chain", response_model=AuditVerifyResponse)
def verify_audit_chain():
    """
    Cryptographically verifies the end-to-end SHA-256 HMAC audit log hash chain.
    Validates that no historical record has been altered, deleted, or injected.
    """
    sync_db = get_sync_session()
    try:
        result = AuditService.verify_chain(sync_db)
        return AuditVerifyResponse(
            is_valid=result["is_valid"],
            total_entries_verified=result["total_entries_verified"],
            status=result["status"],
            genesis_hash=result.get("genesis_hash"),
            latest_hash=result.get("latest_hash"),
            tampered_entry_id=result.get("tampered_entry_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit chain verification error: {str(e)}")
    finally:
        sync_db.close()
