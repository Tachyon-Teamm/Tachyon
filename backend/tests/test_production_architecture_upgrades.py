import unittest
import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization.data_profiler import DataProfiler, DataQualityReport
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.matching.cluster_engine import ClusterEngine, DSU
from app.services.governance.cnmc_minter import calculate_verhoeff_checksum, validate_verhoeff
from app.services.governance.golden_record_service import GoldenRecordService
from app.services.governance.audit_service import AuditService
from app.services.integration.webhook_service import WebhookService

class TestProductionArchitectureUpgrades(unittest.TestCase):

    # 1. Test DataProfiler (Stage 1: Ingest + Validate)
    def test_data_profiler_batch_scoring(self):
        records = [
            {"material_code": "MAT-001", "short_description": "VLV GATE 6IN 300# CS FLG", "uom": "EA"},
            {"material_code": "MAT-002", "short_description": "CABLE 3CX240 SQMM 11KV XLPE", "uom": "MTR"},
            {"material_code": "MAT-003", "short_description": "BOLT HEX M12 X 50MM 8.8", "uom": "NOS"},
            {"material_code": "", "short_description": "UNKNOWN UNCODED ITEM", "uom": "INVALID"}
        ]
        report = DataProfiler.profile_records(records)
        self.assertEqual(report.total_rows, 4)
        self.assertEqual(report.completeness_rate, 0.75)
        self.assertEqual(report.valid_uom_rate, 0.75)
        self.assertGreaterEqual(report.quality_score, 0.60)
        self.assertTrue(report.to_dict()["is_acceptable"])

    # 2. Test Multi-Sector Lexicon Pre-Expansion (Stage 2: Normalize)
    def test_multi_sector_lexicon_expansion(self):
        # Electrical
        elec_text = "LT CBL 3CX240 SQMM FOR XFRMR SWGR"
        clean_elec = DomainLexicon.preprocess_text(elec_text)
        self.assertIn("LOW TENSION CABLE", clean_elec)
        self.assertIn("TRANSFORMER", clean_elec)
        self.assertIn("SWITCHGEAR", clean_elec)

        # Steel / Fasteners
        fastener_text = "M16 BLT FASTNR"
        clean_fastener = DomainLexicon.preprocess_text(fastener_text)
        self.assertIn("BOLT", clean_fastener)
        self.assertIn("FASTENER", clean_fastener)

        # Pre-expanded abbreviations (CS vs SS)
        cs_text = "VLV GATE 6IN 300# CS FLG"
        ss_text = "VLV GATE 6IN 300# SS FLG"
        self.assertIn("CARBON STEEL", DomainLexicon.preprocess_text(cs_text))
        self.assertIn("STAINLESS STEEL", DomainLexicon.preprocess_text(ss_text))

    # 3. Test Dynamic Spec Extractor for Non-O&G (Stage 3: Attribute Extraction)
    def test_spec_extractor_electrical_and_fasteners(self):
        # Electrical extraction
        cbl_desc = "CABLE XLPE 3CX240 SQMM 11KV 630A 3P"
        specs = SpecExtractor.extract_specs(cbl_desc)
        self.assertEqual(specs["item_noun"], "CABLE")
        self.assertEqual(specs["voltage_rating"], "11KV")
        self.assertEqual(specs["current_rating"], "630A")
        self.assertEqual(specs["pole_count"], "3P")
        self.assertIn("voltage_rating", specs["technical_attributes"])
        self.assertEqual(specs["technical_attributes"]["voltage_rating"], "11KV")

        # Fastener extraction
        bolt_desc = "HEX BOLT M16 X 65 MM GRADE 8.8"
        bolt_specs = SpecExtractor.extract_specs(bolt_desc)
        self.assertEqual(bolt_specs["item_noun"], "FASTENER")
        self.assertEqual(bolt_specs["thread_size"], "M16")
        self.assertEqual(bolt_specs["length"], "65 MM")
        self.assertEqual(bolt_specs["technical_attributes"]["thread_size"], "M16")

    # 4. Test Multi-Sector Safety Guardrails (Stage 6: Deterministic Matching)
    def test_safety_guardrails_electrical_and_fasteners(self):
        # Electrical voltage veto (230V vs 415V)
        specs_230v = {"item_noun": "CONTACTOR", "voltage_rating": "230V"}
        specs_415v = {"item_noun": "CONTACTOR", "voltage_rating": "415V"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_230v, specs_415v)
        self.assertTrue(is_vetoed)
        self.assertIn("Voltage rating conflict", reason)
        self.assertEqual(route, "REJECT")

        # Fastener thread size veto (M12 vs M16)
        specs_m12 = {"item_noun": "FASTENER", "thread_size": "M12"}
        specs_m16 = {"item_noun": "FASTENER", "thread_size": "M16"}
        is_vetoed_f, reason_f, route_f = SafetyGuardrails.evaluate_pair(specs_m12, specs_m16)
        self.assertTrue(is_vetoed_f)
        self.assertIn("Fastener thread size mismatch", reason_f)
        self.assertEqual(route_f, "REJECT")

    # 5. Test Adaptive Missing-Price Fallback Scorer (Stage 8: Confidence + Evidence)
    def test_adaptive_scorer_rebalancing(self):
        vec_a = [0.8, 0.4, 0.1]
        vec_b = [0.8, 0.4, 0.1]
        specs_a = {"item_noun": "FASTENER", "thread_size": "M16", "length": "50 MM"}
        specs_b = {"item_noun": "FASTENER", "thread_size": "M16", "length": "50 MM"}
        
        # Procurement completely missing (confidential or unreleased)
        proc_empty_a = {}
        proc_empty_b = {}

        # Default weights without proc should redistribute 25% to semantic and attribute
        res = CompositeScorer.compute_composite(
            vec_a, vec_b, specs_a, specs_b, proc_empty_a, proc_empty_b,
            category="FASTENER"
        )
        self.assertEqual(res["weights"]["procurement"], 0.0)
        self.assertGreater(res["weights"]["attribute"], 0.65)
        self.assertGreaterEqual(res["composite_score"], 0.90)
        self.assertEqual(res["confidence_tier"], "HIGH")

    # 6. Test ClusterEngine Transitive Closure & Coherence (Stage 9: Human Validation)
    def test_cluster_engine_transitive_closure(self):
        # A(1) ~ B(2) (0.95), B(2) ~ C(3) (0.94), A(1) ~ C(3) (0.93)
        candidate_edges = [
            {"material_a_id": 1, "material_b_id": 2, "composite_score": 0.95, "is_vetoed": False},
            {"material_a_id": 2, "material_b_id": 3, "composite_score": 0.94, "is_vetoed": False},
            {"material_a_id": 1, "material_b_id": 3, "composite_score": 0.93, "is_vetoed": False},
            # Disjoint material D(4)
            {"material_a_id": 4, "material_b_id": 5, "composite_score": 0.91, "is_vetoed": False}
        ]
        res = ClusterEngine.form_clusters(candidate_edges, min_score=0.70)
        self.assertEqual(res["total_clusters"], 2)
        # 1, 2, and 3 should belong to the exact same cluster
        c_1 = res["material_to_cluster"][1]
        c_2 = res["material_to_cluster"][2]
        c_3 = res["material_to_cluster"][3]
        self.assertEqual(c_1, c_2)
        self.assertEqual(c_2, c_3)

        # 4 and 5 should belong to a different cluster
        c_4 = res["material_to_cluster"][4]
        self.assertNotEqual(c_1, c_4)

    # 7. Test Verhoeff Checksum (Stage 11: CNMC Code Minter)
    def test_verhoeff_checksum_validation(self):
        seq_num = "00001042"
        checksum = calculate_verhoeff_checksum(seq_num)
        self.assertIsInstance(checksum, int)
        full_code = f"{seq_num}{checksum}"
        self.assertTrue(validate_verhoeff(full_code))
        
        # Test typo detection
        corrupted_code = f"{seq_num}9" if checksum != 9 else f"{seq_num}0"
        self.assertFalse(validate_verhoeff(corrupted_code))

    # 8. Test GoldenRecord ISO 8000 Multi-Sector Synthesis (Stage 10: Standardize)
    def test_golden_record_multi_sector_synthesis(self):
        class MockElectricalMat:
            def __init__(self, noun, volt, curr, poles):
                self.item_noun = noun
                self.technical_attributes = {
                    "item_noun": noun,
                    "voltage_rating": volt,
                    "current_rating": curr,
                    "pole_count": poles
                }
                self.base_uom = "EA"
                self.extracted_attributes = self.technical_attributes

        mats = [
            MockElectricalMat("CONTACTOR", "415V", "100A", "3 POLE"),
            MockElectricalMat("CONTACTOR", "415V", "100A", "3 POLE")
        ]
        synth = GoldenRecordService.synthesize_iso8000_description(mats)
        self.assertEqual(synth["item_noun"], "CONTACTOR")
        self.assertIn("415V", synth["standardized_description"])
        self.assertIn("100A", synth["standardized_description"])
        self.assertEqual(synth["technical_attributes"]["voltage_rating"], "415V")

    # 9. Test Webhook Event Signature (Stage 14: SAP/ERP Export or API)
    def test_webhook_signature_generation(self):
        payload = {"event_type": "material.minted", "cnmc": "CNMC-00001042-8"}
        sig1 = WebhookService.generate_hmac_signature(payload, "secret-key-123")
        sig2 = WebhookService.generate_hmac_signature(payload, "secret-key-123")
        self.assertEqual(sig1, sig2)
        
        sig_diff = WebhookService.generate_hmac_signature(payload, "different-key")
        self.assertNotEqual(sig1, sig_diff)

    # 10. Test Audit Service Cryptographic Chaining
    def test_audit_cryptographic_chaining(self):
        hash1 = AuditService._compute_entry_hash(
            "GENESIS", "CNMC_MINTED", "CNMC_CODE", "CNMC-00001042-8", 1, {"materials_count": 3}
        )
        self.assertEqual(len(hash1), 64) # 256-bit hex string
        
        hash2 = AuditService._compute_entry_hash(
            hash1, "CROSSWALK_REGISTERED", "CROSSWALK", "MAP-001", 1, {"status": "ACTIVE"}
        )
        self.assertEqual(len(hash2), 64)
        self.assertNotEqual(hash1, hash2)

    # 11. Test SAP MATMAS05 IDoc Generator Structure
    def test_sap_matmas05_idoc_structure(self):
        from unittest.mock import MagicMock
        from app.api.v1.integration.sap import generate_matmas_idoc
        
        mock_gr = MagicMock()
        mock_gr.id = 1
        mock_gr.cnmc_code.code = "CNMC-00001042-8"
        mock_gr.base_uom = "EA"
        mock_gr.standardized_description = "VALVE, GATE, 6 INCH, CLASS 300#"
        mock_gr.version_number = 1
        mock_gr.technical_attributes = {"nominal_size": "6 INCH"}
        
        mock_db = MagicMock()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_gr]
        
        res = generate_matmas_idoc(cnmc_codes=["CNMC-00001042-8"], db=mock_db)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["idoc_type"], "MATMAS05")
        self.assertEqual(res["total_idocs"], 1)
        self.assertEqual(res["payloads"][0]["IDOC"]["E1MARAM"]["MATNR"], "CNMC-00001042-8")

    # 12. Test GeM Catalog Syndication Structure
    def test_gem_catalog_syndication_structure(self):
        from unittest.mock import MagicMock
        from app.api.v1.integration.gem import sync_gem_catalog

        mock_gr = MagicMock()
        mock_gr.id = 1
        mock_gr.item_noun = "VALVE, GATE"
        mock_gr.cnmc_code.code = "CNMC-00001042-8"
        mock_gr.standardized_description = "VALVE, GATE, 6 INCH, CLASS 300#"
        mock_gr.base_uom = "EA"
        mock_gr.nominal_size = "6 INCH"
        mock_gr.pressure_class = "CLASS 300#"
        mock_gr.moc = "ASTM A216 WCB"
        mock_gr.standard_spec = "ASME B16.34"
        mock_gr.end_connection = "FLANGED RF"
        mock_gr.version_number = 1
        mock_gr.technical_attributes = {}
        mock_gr.canonical_attributes = {}

        mock_db = MagicMock()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_gr]

        res = sync_gem_catalog(cnmc_codes=["CNMC-00001042-8"], db=mock_db)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_syndicated"], 1)
        item = res["gem_catalog_items"][0]
        self.assertEqual(item["national_material_code"], "CNMC-00001042-8")
        self.assertIn("pki_signature_hash", item)
        self.assertEqual(len(item["pki_signature_hash"]), 64)

if __name__ == "__main__":
    unittest.main()
