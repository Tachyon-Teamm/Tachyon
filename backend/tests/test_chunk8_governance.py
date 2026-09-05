import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.database import get_sync_db
from app.models.models import Material, MatchCandidate, ReviewQueue, CPSE, MatchJob, CNMCCode, Crosswalk, GoldenRecord
from app.services.governance.cnmc_minter import CNMCMinter, validate_verhoeff
from app.services.governance.audit_service import AuditService

def test_chunk8_verhoeff_and_cnmc_minting():
    db = next(get_sync_db())
    try:
        gr = db.query(GoldenRecord).first()
        if not gr:
            gr = GoldenRecord(
                standardized_description="VALVE, BALL, 2 INCH, 150#",
                item_noun="VALVE",
                modifier="BALL",
                is_active=True
            )
            db.add(gr)
            db.commit()
            db.refresh(gr)

        # Mint next code
        code = CNMCMinter.mint_next_cnmc(db, golden_record_id=gr.id)
        assert code.startswith("CNMC-")
        assert validate_verhoeff(code) is True
        
        # Test checksum rejects typos
        corrupted = code[:-1] + ("0" if code[-1] != "0" else "1")
        assert validate_verhoeff(corrupted) is False
    finally:
        db.close()

def test_chunk8_audit_tamper_evident_chain():
    db = next(get_sync_db())
    try:
        log1 = AuditService.log_action(db, "TEST_ACTION_1", "TEST", "1", 1, {"k": 1})
        log2 = AuditService.log_action(db, "TEST_ACTION_2", "TEST", "2", 1, {"k": 2})
        db.commit()
        
        assert log2.evidence["_prev_hash"] == log1.evidence["_hash"]
        assert log1.evidence["_hash"] != "GENESIS"
    finally:
        db.close()

def test_chunk8_bulk_approve_dual_payload_support():
    client = TestClient(app)
    # Test raw array payload
    res1 = client.post("/api/v1/review/bulk-approve", json=["non_existent_cluster_1"])
    assert res1.status_code == 200
    assert res1.json()["status"] == "SUCCESS"
    
    # Test object payload
    res2 = client.post("/api/v1/review/bulk-approve", json={"cluster_group_ids": ["non_existent_cluster_2"], "reviewer_notes": "Tested object"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "SUCCESS"
