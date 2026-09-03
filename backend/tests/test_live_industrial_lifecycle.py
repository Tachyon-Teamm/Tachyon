import time
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.database import get_sync_db
from app.models.models import (
    Material, CPSE, IngestionBatch, MatchJob, MatchCandidate,
    ReviewQueue, GoldenRecord, CNMCCode, Crosswalk, ProcurementHistory,
    MaterialEmbedding
)
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.embeddings import EmbeddingService
from app.services.matching.matcher_engine import MatcherEngine
from app.services.governance.cnmc_minter import validate_verhoeff

def test_complete_industrial_lifecycle_end_to_end():
    client = TestClient(app)
    db = next(get_sync_db())
    
    try:
        # Step 1: Ensure CPCL and IOCL CPSEs exist
        cpcl = db.query(CPSE).filter(CPSE.code == "CPCL").first()
        if not cpcl:
            cpcl = CPSE(code="CPCL", name="Chennai Petroleum Corporation Limited", sector="OIL_AND_GAS")
            db.add(cpcl)
            db.flush()
            
        iocl = db.query(CPSE).filter(CPSE.code == "IOCL").first()
        if not iocl:
            iocl = CPSE(code="IOCL", name="Indian Oil Corporation Limited", sector="OIL_AND_GAS")
            db.add(iocl)
            db.flush()
            
        ts = int(time.time() * 1000)
        code_a = f"TEST-CPCL-{ts}"
        code_b = f"TEST-IOCL-{ts}"

        # Material 1: CPCL
        desc_a = "VLV GATE 6IN 300# CS FLG"
        specs_a = SpecExtractor.extract_specs(desc_a)
        mat_a = Material(
            cpse_id=cpcl.id,
            material_code=code_a,
            short_description=desc_a,
            uom=UOMNormalizer.normalize_uom("Nos"),
            base_uom="EA",
            item_noun=specs_a.get("item_noun"),
            nominal_size=specs_a.get("nominal_size"),
            pressure_class=specs_a.get("pressure_class"),
            moc=specs_a.get("moc"),
            schedule=specs_a.get("schedule"),
            end_connection=specs_a.get("end_connection"),
            standard_spec=specs_a.get("standard_spec"),
            clean_part_number=specs_a.get("clean_part_number"),
            extracted_attributes=specs_a,
            status="ACTIVE"
        )
        db.add(mat_a)
        db.flush()


        emb_a = EmbeddingService.generate_embedding(desc_a)
        db.add(MaterialEmbedding(material_id=mat_a.id, embedding=emb_a, sparse_vector={"valve": 1.0, "gate": 1.0}))
        db.add(ProcurementHistory(
            material_id=mat_a.id,
            cpse_id=cpcl.id,
            po_number="PO-CPCL-001",
            vendor_name="L&T Valves Ltd",
            vendor_normalized=VendorNormalizer.normalize_vendor("L&T Valves Ltd"),
            unit_price=12500.0,
            quantity=10.0,
            currency="INR"
        ))

        # Material 2: IOCL
        desc_b = "VALVE, GATE, 150MM, CL300, WCB"
        specs_b = SpecExtractor.extract_specs(desc_b)
        mat_b = Material(
            cpse_id=iocl.id,
            material_code=code_b,
            short_description=desc_b,
            uom=UOMNormalizer.normalize_uom("EA"),
            base_uom="EA",
            item_noun=specs_b.get("item_noun"),
            nominal_size=specs_b.get("nominal_size"),
            pressure_class=specs_b.get("pressure_class"),
            moc=specs_b.get("moc"),
            schedule=specs_b.get("schedule"),
            end_connection=specs_b.get("end_connection"),
            standard_spec=specs_b.get("standard_spec"),
            clean_part_number=specs_b.get("clean_part_number"),
            extracted_attributes=specs_b,
            status="ACTIVE"
        )
        db.add(mat_b)
        db.flush()

        emb_b = EmbeddingService.generate_embedding(desc_b)
        db.add(MaterialEmbedding(material_id=mat_b.id, embedding=emb_b, sparse_vector={"valve": 1.0, "gate": 1.0}))
        db.add(ProcurementHistory(
            material_id=mat_b.id,
            cpse_id=iocl.id,
            po_number="PO-IOCL-002",
            vendor_name="Larsen & Toubro",
            vendor_normalized=VendorNormalizer.normalize_vendor("Larsen & Toubro"),
            unit_price=11800.0,
            quantity=15.0,
            currency="INR"
        ))

        db.commit()

        # Step 3: Run Matcher Engine
        job = MatchJob(status="PENDING", parameters={"test": True})
        db.add(job)
        db.commit()

        job_result = MatcherEngine.execute_matching_job(db, job.id)
        assert job_result["status"] == "COMPLETED"
        assert job_result["candidates_found"] >= 1

        # Check candidate between mat_a and mat_b
        cand = db.query(MatchCandidate).filter(
            ((MatchCandidate.material_a_id == mat_a.id) & (MatchCandidate.material_b_id == mat_b.id)) |
            ((MatchCandidate.material_a_id == mat_b.id) & (MatchCandidate.material_b_id == mat_a.id))
        ).first()

        assert cand is not None, "Candidate pair must be generated"
        assert cand.safety_veto is False, "Safety guardrails must pass for identical specs"
        assert cand.composite_score >= 0.70, f"Composite score should be high, got {cand.composite_score}"
        assert cand.cluster_group_id is not None, "Candidate must be assigned to a cluster group"

        cluster_id = cand.cluster_group_id

        # Step 4: Governance Review Action - Approve Cluster
        action_payload = {
            "cluster_group_id": cluster_id,
            "decision_type": "IDENTICAL",
            "reviewer_notes": "Industrial verification test approval"
        }
        res_action = client.post("/api/v1/review/action", json=action_payload)
        assert res_action.status_code == 200, f"Review action failed: {res_action.text}"
        action_data = res_action.json()
        assert action_data["status"] == "SUCCESS"
        cnmc_code = action_data.get("minted_cnmc") or action_data.get("cnmc_code")
        assert cnmc_code is not None, f"Expected minted_cnmc in {action_data}"

        # Step 5: Verify CNMC Code & Verhoeff Checksum
        assert cnmc_code.startswith("CNMC-")
        assert validate_verhoeff(cnmc_code) is True, f"Minted CNMC {cnmc_code} must satisfy Verhoeff checksum"

        # Step 6: Verify Bidirectional Crosswalk Lookup
        lookup_res = client.get(f"/api/v1/crosswalk/lookup?local_code={code_a}&cpse_code=CPCL")
        assert lookup_res.status_code == 200
        lookup_data = lookup_res.json()
        assert lookup_data["found"] is True
        assert lookup_data["cnmc_details"]["cnmc_code"] == cnmc_code
        
        # Verify cross-ref CPSE mappings are populated
        cross_mappings = lookup_data["cnmc_details"]["crosswalk_links"]
        assert len(cross_mappings) >= 2, "Must map to both CPCL and IOCL records"

        # Step 7: Verify SAP LSMW CSV Export contains the newly approved item
        lsmw_res = client.get("/api/v1/export/sap-lsmw-csv")
        assert lsmw_res.status_code == 200
        assert cnmc_code in lsmw_res.text
        assert "MM01" in lsmw_res.text
        assert "ERSA" in lsmw_res.text

        # Step 8: Verify SAP S/4HANA MATMAS05 IDoc Export
        idoc_res = client.post("/api/v1/integration/sap/idoc-export", json=[cnmc_code])
        assert idoc_res.status_code == 200
        idoc_data = idoc_res.json()
        assert idoc_data["idoc_type"] == "MATMAS05"
        assert idoc_data["total_idocs"] >= 1
        payload0 = idoc_data["payloads"][0]["IDOC"]
        assert payload0["EDI_DC40"]["IDOCTYP"] == "MATMAS05"
        assert payload0["E1MARAM"]["MATNR"] == cnmc_code

        # Step 9: Verify Government e-Marketplace (GeM) Syndication
        gem_res = client.post("/api/v1/integration/gem/catalog-sync", json=[cnmc_code])
        assert gem_res.status_code == 200
        gem_data = gem_res.json()
        assert gem_data["status"] == "SUCCESS"
        assert gem_data["total_syndicated"] >= 1
        gem_item = gem_data["gem_catalog_items"][0]
        assert gem_item["national_material_code"] == cnmc_code
        assert "golden_parameters" in gem_item
        assert "pki_signature_hash" in gem_item
        assert len(gem_item["pki_signature_hash"]) == 64, "SHA-256 hash length must be 64 characters"

    finally:
        db.close()
