import io
import time
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from app.main import app
from app.core.database import get_sync_db
from app.models.models import (
    CPSE, IngestionBatch, RawMaterial, NormalizedMaterial, Material,
    MaterialEmbedding, ProcurementHistory, MatchCandidate, ReviewQueue,
    GoldenRecord, CNMCCode, Crosswalk, AuditLog
)
from app.tasks.ingestion_tasks import process_ingestion_batch_task
from app.services.matching.matcher_engine import MatcherEngine
from app.services.governance.cnmc_minter import validate_verhoeff

def test_pure_data_flow_chunk1_to_chunk9_complete():
    """
    Forensic verification of the pure continuous data flow across all 9 chunks:
      Chunk 1: Upload (file streaming & claim-check)
      Chunk 2: Column Mapping & Live Preview Recalculation
      Chunk 3: Batch Start (Raw Staging DB)
      Chunk 4: Normalization (Silver Normalized & Gold Materials)
      Chunk 5: Vector Encoding (pgvector 384-d Embeddings)
      Chunk 6: Matching & Safety Invariant Vetoes
      Chunk 7: Tri-factor Composite Scoring & Review Queue
      Chunk 8: Governance Review (ISO 8000 + Verhoeff CNMC Minting + Audit Log)
      Chunk 9: Crosswalk Reverse Lookup & SAP LSMW Export
    """
    client = TestClient(app)
    db = next(get_sync_db())

    try:
        # Ensure CPSEs exist
        for code, name in [("CPCL", "Chennai Petroleum"), ("IOCL", "Indian Oil"), ("BPCL", "Bharat Petroleum")]:
            c = db.query(CPSE).filter(CPSE.code == code).first()
            if not c:
                db.add(CPSE(code=code, name=name, sector="OIL_AND_GAS"))
        db.commit()

        ts = int(time.time() * 1000)
        code_cpcl = f"FLOW-CPCL-{ts}"
        code_iocl = f"FLOW-IOCL-{ts}"

        # =================================================================
        # CHUNK 1: Upload & Header Detection
        # =================================================================
        csv_content = (
            "MAT_CODE,SPECIFICATION,UOM_CODE,UNIT_RATE,SUPPLIER,COMMODITY_CODE\n"
            f"{code_cpcl},VALVE GATE 6IN 300# CS FLG,Nos,12500.0,L&T Valves Ltd,84818030\n"
        ).encode("utf-8")

        res_c1 = client.post(
            "/api/v1/ingestion/detect-columns",
            files={"file": ("test_flow_cpcl.csv", io.BytesIO(csv_content), "text/csv")},
            data={"cpse_code": "CPCL"}
        )
        assert res_c1.status_code == 200, f"Chunk 1 failed: {res_c1.text}"
        c1_data = res_c1.json()
        assert "upload_id" in c1_data
        assert "MAT_CODE" in c1_data["detected_columns"]
        upload_id = c1_data["upload_id"]

        # =================================================================
        # CHUNK 2: Column Mapping & Dynamic Preview Recalculation
        # =================================================================
        mapping_config = {
            "MAT_CODE": "material_code",
            "SPECIFICATION": "short_description",
            "UOM_CODE": "uom",
            "UNIT_RATE": "base_price",
            "SUPPLIER": "vendor_name",
            "COMMODITY_CODE": "hsn_code"
        }

        res_c2 = client.post(
            "/api/v1/ingestion/preview",
            json={
                "preview_rows": c1_data["preview_rows"],
                "mapping_config": mapping_config
            }
        )
        assert res_c2.status_code == 200, f"Chunk 2 preview failed: {res_c2.text}"
        c2_data = res_c2.json()
        assert len(c2_data["preview_rows"]) >= 1
        assert c2_data["preview_rows"][0]["_preview_specs"]["item_noun"] == "VALVE, GATE"
        assert c2_data["preview_rows"][0]["_preview_uom"] == "EA"

        # =================================================================
        # CHUNK 3: Batch Start (Staging into raw_materials)
        # =================================================================
        import json
        res_c3 = client.post(
            "/api/v1/ingestion/start-batch",
            data={
                "upload_id": upload_id,
                "cpse_code": "CPCL",
                "mapping_config_json": json.dumps(mapping_config)
            }
        )
        assert res_c3.status_code == 200, f"Chunk 3 failed: {res_c3.text}"
        batch_id_cpcl = res_c3.json()["id"]

        # Verify Bronze Layer storage
        raw_recs = db.query(RawMaterial).filter(RawMaterial.batch_id == batch_id_cpcl).all()
        assert len(raw_recs) >= 1

        # =================================================================
        # CHUNK 4: Normalization (Silver Staging & Gold Active Layers)
        # CHUNK 5: Vector Encoding (pgvector 384-d Embeddings)
        # =================================================================
        # Wait for background worker completion (simulating frontend polling)
        for _ in range(50):
            b_res = client.get(f"/api/v1/ingestion/batch/{batch_id_cpcl}/status")
            if b_res.status_code == 200 and b_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break
            time.sleep(0.1)

        db.expire_all()
        # Check Silver Layer
        silver = db.query(NormalizedMaterial).filter(NormalizedMaterial.material_code == code_cpcl).first()
        assert silver is not None
        assert silver.base_uom == "EA"
        assert silver.status == "PROMOTED"

        # Check Gold Layer
        gold_cpcl = db.query(Material).filter(Material.material_code == code_cpcl).first()
        assert gold_cpcl is not None
        assert gold_cpcl.item_noun == "VALVE, GATE"
        assert gold_cpcl.nominal_size == "6 INCH (150 MM)"
        assert gold_cpcl.pressure_class == "CLASS 300#"

        # Check Chunk 5 Vector Embedding
        emb_cpcl = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == gold_cpcl.id).first()
        assert emb_cpcl is not None
        assert len(emb_cpcl.embedding) == 384

        # Ingest IOCL sister material for matching
        csv_iocl = (
            "MAT_CODE,SPECIFICATION,UOM_CODE,UNIT_RATE,SUPPLIER,COMMODITY_CODE\n"
            f"{code_iocl},VALVE GATE 150MM CL300 WCB,EA,10800.0,Larsen & Toubro Ltd,84818030\n"
        ).encode("utf-8")
        res_iocl = client.post(
            "/api/v1/ingestion/detect-columns",
            files={"file": ("test_flow_iocl.csv", io.BytesIO(csv_iocl), "text/csv")},
            data={"cpse_code": "IOCL"}
        )
        iocl_upload_id = res_iocl.json()["upload_id"]
        res_iocl_b = client.post(
            "/api/v1/ingestion/start-batch",
            data={
                "upload_id": iocl_upload_id,
                "cpse_code": "IOCL",
                "mapping_config_json": json.dumps(mapping_config)
            }
        )
        batch_id_iocl = res_iocl_b.json()["id"]

        # Wait for IOCL background batch completion
        for _ in range(50):
            b_res = client.get(f"/api/v1/ingestion/batch/{batch_id_iocl}/status")
            if b_res.status_code == 200 and b_res.json()["status"] in ["COMPLETED", "FAILED"]:
                break
            time.sleep(0.1)

        db.expire_all()
        gold_iocl = db.query(Material).filter(Material.material_code == code_iocl).first()
        assert gold_iocl is not None

        # =================================================================
        # CHUNK 6: Matching & Safety Invariant Vetoes
        # CHUNK 7: Tri-Factor Composite Scoring & Review Queue Enqueueing
        # =================================================================
        res_trigger = client.post("/api/v1/matching/trigger")
        assert res_trigger.status_code == 200
        match_job_id = res_trigger.json()["job_id"]

        # Run matcher engine
        match_result = MatcherEngine.execute_cross_cpse_matching(db, match_job_id)
        assert match_result["status"] == "COMPLETED"

        # Verify Candidate & Review Queue
        cand = db.query(MatchCandidate).filter(
            ((MatchCandidate.material_a_id == gold_cpcl.id) & (MatchCandidate.material_b_id == gold_iocl.id)) |
            ((MatchCandidate.material_a_id == gold_iocl.id) & (MatchCandidate.material_b_id == gold_cpcl.id))
        ).first()
        assert cand is not None
        assert cand.safety_veto is False
        assert cand.composite_score >= 0.70

        cluster_id = cand.cluster_group_id
        assert cluster_id is not None

        review_item = db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == cluster_id).first()
        assert review_item is not None
        assert review_item.status == "PENDING"

        # =================================================================
        # CHUNK 8: Governance Review Gate (ISO 8000 + CNMC Minting + Audit)
        # =================================================================
        action_res = client.post("/api/v1/review/action", json={
            "cluster_group_id": cluster_id,
            "decision_type": "IDENTICAL",
            "reviewer_notes": "Continuous flow verification approval"
        })
        assert action_res.status_code == 200, f"Review action failed: {action_res.text}"
        act_json = action_res.json()
        assert act_json["status"] == "SUCCESS"
        minted_cnmc = act_json["minted_cnmc"]
        assert minted_cnmc.startswith("CNMC-")
        assert validate_verhoeff(minted_cnmc) is True

        # Verify Golden Record has technical_attributes
        golden_rec = db.query(GoldenRecord).filter(GoldenRecord.review_queue_id == review_item.id).first()
        assert golden_rec is not None
        assert "item_noun" in golden_rec.canonical_attributes or golden_rec.item_noun == "VALVE, GATE"

        # Verify Audit Log
        audit = db.query(AuditLog).filter(AuditLog.entity_id == minted_cnmc).first()
        assert audit is not None
        assert "_hash" in audit.evidence

        # =================================================================
        # CHUNK 9: Crosswalk Reverse Lookup & SAP Export
        # =================================================================
        lookup_res = client.get(f"/api/v1/crosswalk/lookup?local_code={code_cpcl}&cpse_code=CPCL")
        assert lookup_res.status_code == 200
        lookup_data = lookup_res.json()
        assert lookup_data["found"] is True
        assert lookup_data["cnmc_details"]["cnmc_code"] == minted_cnmc
        
        # Verify sister IOCL mapping is present
        sister_codes = [link["local_material_code"] for link in lookup_data["cnmc_details"]["crosswalk_links"]]
        assert code_iocl in sister_codes

        # Verify SAP LSMW Export
        export_res = client.get("/api/v1/export/sap-lsmw-csv")
        assert export_res.status_code == 200
        assert minted_cnmc in export_res.text
        assert "MM01" in export_res.text
        assert code_cpcl in export_res.text

    finally:
        db.close()
