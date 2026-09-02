import hashlib
import json
from typing import Dict, Any, Optional
try:
    from sqlalchemy.orm import Session
    from sqlalchemy import desc
    from app.models.models import AuditLog
except ImportError:
    Session = Any  # type: ignore
    desc = Any  # type: ignore
    class AuditLog:  # type: ignore
        id = 0
        def __init__(self, **kwargs): pass

class AuditService:
    """
    CERT-In Compliant Cryptographic Audit Service.
    Implements SHA-256 tamper-evident hash chaining across consecutive audit entries.
    """

    @staticmethod
    def _compute_entry_hash(prev_hash: str, action: str, entity_type: Optional[str], entity_id: Optional[str], user_id: Optional[int], evidence: Dict[str, Any]) -> str:
        payload_str = f"{prev_hash}|{action}|{entity_type or ''}|{entity_id or ''}|{user_id or ''}|{json.dumps(evidence, sort_keys=True)}"
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[int] = None,
        evidence: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        evidence_dict = dict(evidence or {})

        # Fetch latest audit entry hash to create tamper-evident chain
        last_entry = db.query(AuditLog).order_by(desc(AuditLog.id)).first()
        prev_hash = "GENESIS"
        if last_entry and last_entry.evidence and isinstance(last_entry.evidence, dict):
            prev_hash = last_entry.evidence.get("_hash", "GENESIS")

        # Compute tamper-evident hash
        current_hash = AuditService._compute_entry_hash(
            prev_hash, action, entity_type, entity_id, user_id, evidence_dict
        )
        evidence_dict["_prev_hash"] = prev_hash
        evidence_dict["_hash"] = current_hash

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            evidence=evidence_dict
        )
        db.add(log_entry)
        db.flush()
        return log_entry
