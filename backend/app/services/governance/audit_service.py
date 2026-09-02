from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import AuditLog

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[int] = None,
        evidence: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            evidence=evidence or {}
        )
        db.add(log_entry)
        db.flush()
        return log_entry
