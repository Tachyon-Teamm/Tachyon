from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import CNMCCode, GoldenRecord
from app.core.config import settings

class CNMCMinter:
    """
    Single-Authority CNMC Code Generator.
    Mints strictly unique Common National Material Codes: CNMC-XXXXXXXX.
    """

    @classmethod
    def mint_next_cnmc(cls, db: Session, golden_record_id: int) -> str:
        # Check if already minted for this golden record
        existing = db.query(CNMCCode).filter(CNMCCode.golden_record_id == golden_record_id).first()
        if existing:
            return existing.code

        # Count total existing codes to generate next sequence
        max_id = db.query(func.max(CNMCCode.id)).scalar() or 0
        next_seq = max_id + 1
        
        code_str = f"{settings.CNMC_PREFIX}-{next_seq:0{settings.CNMC_DIGITS}d}"
        
        cnmc_entry = CNMCCode(
            code=code_str,
            golden_record_id=golden_record_id,
            is_active=True
        )
        db.add(cnmc_entry)
        db.flush()
        return code_str
