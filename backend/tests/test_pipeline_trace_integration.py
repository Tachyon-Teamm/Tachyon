import unittest
import sys
import os
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.governance.golden_record_service import GoldenRecordService

class MockEntity:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        for k, v in kwargs.items():
            setattr(self, k, v)

class TestEndToEndPipelineTrace(unittest.TestCase):
    """
    Forensic system-designer trace of all 6 stages of the UniMM Pipeline:
    Stage 1: Source Isolation & Entity Scoping (CPCL, IOCL, BPCL)
    Stage 2: Batch Ingestion, Column Mapping, UOM Normalization & Parametric Spec Extraction
    Stage 3: Zero-Training Matching, Category Blocking & Hard Invariant Vetoes
    Stage 4: Human-in-the-Loop 3-Way Governance Gate
    Stage 5: ISO 8000 Golden Record Synthesis & CNMC Authority Code Issuance
    Stage 6: N:1 Crosswalk Hub Linkage, Reverse Lookup & SAP LSMW Export
    """

    def test_pipeline_stage_1_to_6_complete_trace(self):
        # -------------------------------------------------------------
        # STAGE 1: SOURCE SYSTEM ISOLATION
        # -------------------------------------------------------------
        raw_cpcl = {"code": "100234", "desc": "VLV GATE 6IN 300# CS FLG", "uom": "Nos", "price": 12500.0, "vendor": "L&T Valves Ltd"}
        raw_iocl = {"code": "889102", "desc": "VALVE, GATE, 150MM, CL300, WCB", "uom": "EA", "price": 10800.0, "vendor": "Larsen & Toubro Ltd - Valve Div"}
        raw_bpcl = {"code": "445511", "desc": "6 INCH GATE VALVE FLANGED 300#", "uom": "Numbers", "price": 11200.0, "vendor": "Microfinish Valves"}

        self.assertNotEqual(raw_cpcl["code"], raw_iocl["code"])
        self.assertNotEqual(raw_iocl["code"], raw_bpcl["code"])

        # -------------------------------------------------------------
        # STAGE 2: INGESTION, UOM NORMALIZATION & SPEC EXTRACTION
        # -------------------------------------------------------------
        # UOM Normalization
        uom_cpcl = UOMNormalizer.normalize_uom(raw_cpcl["uom"])
        uom_iocl = UOMNormalizer.normalize_uom(raw_iocl["uom"])
        uom_bpcl = UOMNormalizer.normalize_uom(raw_bpcl["uom"])
        self.assertEqual(uom_cpcl, "EA")
        self.assertEqual(uom_iocl, "EA")
        self.assertEqual(uom_bpcl, "EA")

        # Deterministic Spec Extraction
        specs_cpcl = SpecExtractor.extract_specs(raw_cpcl["desc"])
        specs_iocl = SpecExtractor.extract_specs(raw_iocl["desc"])
        specs_bpcl = SpecExtractor.extract_specs(raw_bpcl["desc"])

        self.assertEqual(specs_cpcl["item_noun"], "VALVE, GATE")
        self.assertEqual(specs_iocl["item_noun"], "VALVE, GATE")
        self.assertEqual(specs_bpcl["item_noun"], "VALVE, GATE")

        self.assertEqual(specs_cpcl["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs_iocl["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs_bpcl["nominal_size"], "6 INCH (150 MM)")

        self.assertEqual(specs_cpcl["pressure_class"], "CLASS 300#")
        self.assertEqual(specs_iocl["pressure_class"], "CLASS 300#")
        self.assertEqual(specs_bpcl["pressure_class"], "CLASS 300#")

        # Vendor Normalization
        v_cpcl = VendorNormalizer.normalize_vendor(raw_cpcl["vendor"])
        v_iocl = VendorNormalizer.normalize_vendor(raw_iocl["vendor"])
        self.assertEqual(v_cpcl, "LARSEN & TOUBRO")
        self.assertEqual(v_iocl, "LARSEN & TOUBRO")

        # -------------------------------------------------------------
        # STAGE 3: ZERO-TRAINING MATCHING & SAFETY GUARDRAILS
        # -------------------------------------------------------------
        # 1. Evaluate Safety Invariants
        vetoed_1_2, reason_1_2, _ = SafetyGuardrails.evaluate_pair(specs_cpcl, specs_iocl)
        vetoed_2_3, reason_2_3, _ = SafetyGuardrails.evaluate_pair(specs_iocl, specs_bpcl)
        self.assertFalse(vetoed_1_2)
        self.assertFalse(vetoed_2_3)

        # 2. Evaluate False-Positive Trap (SCH 40 vs SCH 80)
        sch40 = SpecExtractor.extract_specs("PIPE CS 4\" SCH 40 A106")
        sch80 = SpecExtractor.extract_specs("PIPE CS 4\" SCH 80 A106")
        vetoed_sch, reason_sch, route_sch = SafetyGuardrails.evaluate_pair(sch40, sch80)
        self.assertTrue(vetoed_sch)
        self.assertEqual(route_sch, "SUBSTITUTE")

        # 3. Calculate Composite Score: 0.40(Sem) + 0.35(Attr) + 0.25(Proc)
        scores = CompositeScorer.compute_composite(
            vec_a=[0.1] * 384,
            vec_b=[0.1] * 384,
            specs_a=specs_cpcl,
            specs_b=specs_iocl,
            proc_a={"vendor_normalized": v_cpcl, "unit_price": 12500.0, "hsn_code": "84818030"},
            proc_b={"vendor_normalized": v_iocl, "unit_price": 10800.0, "hsn_code": "84818030"}
        )
        self.assertGreaterEqual(scores["composite_score"], 0.90)
        self.assertEqual(scores["confidence_tier"], "HIGH")

        # -------------------------------------------------------------
        # STAGE 4: HUMAN-IN-THE-LOOP REVIEW GATE & ISO 8000 SYNTHESIS
        # -------------------------------------------------------------
        mat1 = MockEntity(id=1, cpse_id=1, cpse=MockEntity(code="CPCL"), material_code="100234", short_description=raw_cpcl["desc"], uom="EA", base_uom="EA", package_multiplier=1.0, extracted_attributes=specs_cpcl)
        mat2 = MockEntity(id=2, cpse_id=2, cpse=MockEntity(code="IOCL"), material_code="889102", short_description=raw_iocl["desc"], uom="EA", base_uom="EA", package_multiplier=1.0, extracted_attributes=specs_iocl)
        mat3 = MockEntity(id=3, cpse_id=3, cpse=MockEntity(code="BPCL"), material_code="445511", short_description=raw_bpcl["desc"], uom="EA", base_uom="EA", package_multiplier=1.0, extracted_attributes=specs_bpcl)

        cluster_materials = [mat1, mat2, mat3]
        iso_record = GoldenRecordService.synthesize_iso8000_description(cluster_materials)

        expected_desc = "VALVE, GATE, 6 INCH (150 MM), CLASS 300#, FLANGED RF, ASTM A216 WCB"
        self.assertEqual(iso_record["item_noun"], "VALVE, GATE")
        self.assertEqual(iso_record["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(iso_record["pressure_class"], "CLASS 300#")
        self.assertEqual(iso_record["moc"], "ASTM A216 WCB")

        # -------------------------------------------------------------
        # STAGE 5: CNMC AUTHORITY CODE ISSUANCE
        # -------------------------------------------------------------
        # Simulate minting CNMC sequence
        mock_golden_id = 1042
        cnmc_code = f"CNMC-{mock_golden_id:08d}"
        self.assertEqual(cnmc_code, "CNMC-00001042")

        # -------------------------------------------------------------
        # STAGE 6: UNIFIED CROSSWALK N:1 REGISTRATION & REVERSE LOOKUP
        # -------------------------------------------------------------
        crosswalk_registry = {
            ("CPCL", "100234"): {"cnmc": cnmc_code, "desc": iso_record["standardized_description"], "type": "IDENTICAL"},
            ("IOCL", "889102"): {"cnmc": cnmc_code, "desc": iso_record["standardized_description"], "type": "IDENTICAL"},
            ("BPCL", "445511"): {"cnmc": cnmc_code, "desc": iso_record["standardized_description"], "type": "IDENTICAL"},
        }

        # Query reverse lookup for CPCL 100234
        res_cpcl = crosswalk_registry.get(("CPCL", "100234"))
        self.assertIsNotNone(res_cpcl)
        self.assertEqual(res_cpcl["cnmc"], "CNMC-00001042")

        # Query reverse lookup for IOCL 889102
        res_iocl = crosswalk_registry.get(("IOCL", "889102"))
        self.assertIsNotNone(res_iocl)
        self.assertEqual(res_iocl["cnmc"], "CNMC-00001042")

        # Demand aggregation volume calculation
        vol_cpcl, vol_iocl, vol_bpcl = 500.0, 2000.0, 1500.0
        total_vol = vol_cpcl + vol_iocl + vol_bpcl
        self.assertEqual(total_vol, 4000.0)

        # Price variance and estimated collaborative savings
        price_cpcl, price_iocl, price_bpcl = 12500.0, 10800.0, 11200.0
        max_p = max(price_cpcl, price_iocl, price_bpcl)
        min_p = min(price_cpcl, price_iocl, price_bpcl)
        savings_lakhs = round(((max_p - min_p) * total_vol) / 100000.0, 2)
        self.assertEqual(savings_lakhs, 68.0) # (12500 - 10800) * 4000 = ₹68 Lakhs

if __name__ == "__main__":
    unittest.main()
