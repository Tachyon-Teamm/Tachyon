from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import CNMCCode, GoldenRecord
from app.core.config import settings

# Verhoeff Checksum Tables (Industry standard error detection for numeric identifiers)
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def calculate_verhoeff_checksum(number_str: str) -> int:
    c = 0
    reversed_digits = [int(d) for d in reversed(number_str) if d.isdigit()]
    for i, digit in enumerate(reversed_digits):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][digit]]
    return VERHOEFF_INV[c]

def validate_verhoeff(code_str: str) -> bool:
    c = 0
    reversed_digits = [int(d) for d in reversed(code_str) if d.isdigit()]
    for i, digit in enumerate(reversed_digits):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]]
    return c == 0

class CNMCMinter:
    """
    Single-Authority CNMC Code Generator.
    Mints strictly unique Common National Material Codes: CNMC-XXXXXXXX-C.
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
        
        while True:
            seq_str = f"{next_seq:0{settings.CNMC_DIGITS}d}"
            checksum = calculate_verhoeff_checksum(seq_str)
            code_str = f"{settings.CNMC_PREFIX}-{seq_str}-{checksum}"
            if not db.query(CNMCCode).filter(CNMCCode.code == code_str).first():
                break
            next_seq += 1
        
        cnmc_entry = CNMCCode(
            code=code_str,
            golden_record_id=golden_record_id,
            is_active=True
        )
        db.add(cnmc_entry)
        db.flush()
        return code_str

    @classmethod
    def mint_distributed_cnmc(
        cls,
        db: Session,
        golden_record_id: int,
        sector: str = "GEN",
        category_code: str = "0000"
    ) -> str:
        """
        Mints structured multi-sector distributed code:
        CNMC-[SECTOR]-[CATEGORY]-[SEQUENCE]-[CHECKSUM]
        e.g. CNMC-OG-4014-00001042-8
        """
        existing = db.query(CNMCCode).filter(CNMCCode.golden_record_id == golden_record_id).first()
        if existing:
            return existing.code

        max_id = db.query(func.max(CNMCCode.id)).scalar() or 0
        next_seq = max_id + 1
        
        sector_abbr = {
            "OIL_AND_GAS": "OG",
            "POWER": "PW",
            "STEEL": "ST",
            "MINING": "MN",
            "HEAVY_ENG": "HE",
            "CHEMICALS": "CH"
        }.get(sector.upper(), "GN")

        cat_abbr = category_code[:4].upper() if category_code else "0000"
        seq_str = f"{next_seq:0{settings.CNMC_DIGITS}d}"
        numeric_payload = "".join(d for d in (cat_abbr + seq_str) if d.isdigit())
        checksum = calculate_verhoeff_checksum(numeric_payload)
        
        code_str = f"{settings.CNMC_PREFIX}-{sector_abbr}-{cat_abbr}-{seq_str}-{checksum}"
        
        cnmc_entry = CNMCCode(
            code=code_str,
            golden_record_id=golden_record_id,
            is_active=True
        )
        db.add(cnmc_entry)
        db.flush()
        return code_str
