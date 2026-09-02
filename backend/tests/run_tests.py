import unittest
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.normalization.data_profiler import DataProfiler
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.matching.blocking_engine import BlockingEngine
from app.services.matching.cluster_engine import ClusterEngine
from app.services.governance.golden_record_service import GoldenRecordService
from app.services.governance.cnmc_minter import CNMCMinter, validate_verhoeff
from app.tasks.active_learning import ActiveLearningPipeline

class TestUniMMCore(unittest.TestCase):

    def test_uom_and_packaging_multipliers(self):
        self.assertEqual(UOMNormalizer.normalize_uom("Nos"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("NUMBERS"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("pcs"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("MTR"), "MTR")
        self.assertEqual(UOMNormalizer.normalize_uom("KGS"), "KG")

        # 18kg Bucket
        mult1, base1 = UOMNormalizer.extract_packaging_factor("GREASE MOBILITH SHC 100 - 18KG BUCKET", "BKT")
        self.assertEqual(mult1, 18.0)
        self.assertEqual(base1, "KG")

        # 180kg Drum
        mult2, base2 = UOMNormalizer.extract_packaging_factor("MOBILITH SHC 100 - 180KG DRUM", "DRM")
        self.assertEqual(mult2, 180.0)
        self.assertEqual(base2, "KG")

    def test_domain_lexicon_and_hinglish(self):
        raw = "4\" SPIRAL GASKET JAALI WALA 300#"
        clean = DomainLexicon.preprocess_text(raw)
        self.assertIn("SPIRAL WOUND", clean)

        std = DomainLexicon.normalize_standard("ANSI B16.5")
        self.assertEqual(std, "ASME B16.5")

    def test_spec_extractor_valves(self):
        desc = "VLV GATE 6IN 300# CS FLG"
        specs = SpecExtractor.extract_specs(desc)
        self.assertEqual(specs["item_noun"], "VALVE, GATE")
        self.assertEqual(specs["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs["pressure_class"], "CLASS 300#")
        self.assertIn("ASTM A216 WCB", specs["moc"] or "CARBON")
        self.assertEqual(specs["end_connection"], "FLANGED RF")

    def test_spec_extractor_bearing_and_clearance(self):
        desc1 = "BEARING 6205-2RS1 SKF"
        specs1 = SpecExtractor.extract_specs(desc1)
        self.assertEqual(specs1["item_noun"], "BEARING")
        self.assertEqual(specs1["clean_part_number"], "62052RS1")
        self.assertEqual(specs1["brand"], "SKF")

        desc2 = "SKF BEARING NO. 6205 2RS1 / C3"
        specs2 = SpecExtractor.extract_specs(desc2)
        self.assertEqual(specs2["clearance_suffix"], "C3")

    def test_spec_extractor_assembly_vs_spare(self):
        assembly_desc = "MECH SEAL CARTRIDGE PUMP P-101A (SET)"
        spare_desc = "ROTARY SEAL RING FOR PUMP P-101A"
        self.assertTrue(SpecExtractor.extract_specs(assembly_desc)["is_kit_or_assembly"])
        self.assertFalse(SpecExtractor.extract_specs(spare_desc)["is_kit_or_assembly"])

    def test_safety_guardrails_pressure_veto(self):
        specs_150 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 150#"}
        specs_300 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 300#"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_150, specs_300)
        self.assertTrue(is_vetoed)
        self.assertIn("Pressure rating conflict", reason)
        self.assertEqual(route, "SUBSTITUTE")

    def test_safety_guardrails_schedule_veto(self):
        specs_sch40 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 40"}
        specs_sch80 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 80"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_sch40, specs_sch80)
        self.assertTrue(is_vetoed)
        self.assertIn("Wall thickness schedule mismatch", reason)

    def test_safety_guardrails_assembly_veto(self):
        specs_kit = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": True}
        specs_spare = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": False}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_kit, specs_spare)
        self.assertTrue(is_vetoed)
        self.assertIn("Assembly Token Veto", reason)

    def test_multi_sector_guardrails(self):
        # Steel Rebar Mismatch
        rebar_a = {"item_noun": "STEEL REBAR", "steel_grade": "FE 500D"}
        rebar_b = {"item_noun": "STEEL REBAR", "steel_grade": "FE 550D"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(rebar_a, rebar_b)
        self.assertTrue(vetoed)
        self.assertIn("Structural Safety Veto", reason)

        # Mining Conveyor Belt Width Mismatch
        belt_a = {"item_noun": "CONVEYOR BELTING", "belt_width": "1200 MM"}
        belt_b = {"item_noun": "CONVEYOR BELTING", "belt_width": "1400 MM"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(belt_a, belt_b)
        self.assertTrue(vetoed)
        self.assertIn("Mining Safety Veto", reason)

    def test_vendor_normalizer(self):
        self.assertEqual(VendorNormalizer.normalize_vendor("L&T VALVES LTD"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("LARSEN & TOUBRO LTD - VALVE DIV"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("AUDCO INDIA / L&T"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("SKF INDIA"), "SKF")

    def test_composite_scorer_4part_and_missing_po(self):
        vec_a = [1.0, 0.5, 0.2]
        vec_b = [1.0, 0.5, 0.2]
        specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
        specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
        proc_a = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10000.0, "hsn_code": "84818030"}
        proc_b = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10500.0, "hsn_code": "84818030"}

        res = CompositeScorer.compute_composite(
            vec_a=vec_a, vec_b=vec_b, specs_a=specs_a, specs_b=specs_b,
            proc_a=proc_a, proc_b=proc_b, category="VALVE"
        )
        self.assertGreaterEqual(res["composite_score"], 0.90)
        self.assertEqual(res["confidence_tier"], "HIGH")

        # Test Missing PO Signal Dynamic Normalization
        res_no_po = CompositeScorer.compute_composite(
            vec_a=vec_a, vec_b=vec_b, specs_a=specs_a, specs_b=specs_b,
            proc_a={}, proc_b={}, category="VALVE"
        )
        self.assertEqual(res_no_po["weights"]["procurement"], 0.0)
        self.assertAlmostEqual(sum(res_no_po["weights"].values()), 1.0, places=2)

    def test_4tier_blocking_engine(self):
        class MockMat:
            def __init__(self, mid, noun, part=None, size=None, desc=""):
                self.id = mid
                self.item_noun = noun
                self.clean_part_number = part
                self.nominal_size = size
                self.short_description = desc
                self.extracted_attributes = {"item_noun": noun, "clean_part_number": part, "nominal_size": size}

        m1 = MockMat(1, "VALVE, GATE", size="6 INCH (150 MM)", desc="VLV GATE 6IN 300# CS")
        m2 = MockMat(2, "VALVE, GATE", size="6 INCH (150 MM)", desc="6\" GATE VALVE 300# WCB")
        m3 = MockMat(3, "BEARING", part="62052RS1", desc="BEARING 6205-2RS1 SKF")
        m4 = MockMat(4, "BEARING", part="62052RS1", desc="SKF BRG 6205-2RS1")

        dense_dict = {1: [1.0, 0.0], 2: [0.95, 0.05], 3: [0.0, 1.0], 4: [0.0, 0.98]}
        pairs = BlockingEngine.generate_candidate_pairs([m1, m2, m3, m4], dense_dict)
        self.assertIn((1, 2), pairs)
        self.assertIn((3, 4), pairs)
        self.assertNotIn((1, 3), pairs)

    def test_data_quality_profiler(self):
        records = [
            {"material_code": "1001", "short_description": "VALVE GATE 6IN 300# CS FLG", "uom": "EA"},
            {"material_code": "1002", "short_description": "PIPE CS SMLS 4\" SCH 40 A106", "uom": "MTR"},
            {"material_code": "1003", "short_description": "BEARING 6205-2RS1 SKF", "uom": "NOS"}
        ]
        report = DataProfiler.profile_records(records)
        self.assertEqual(report.completeness_rate, 1.0)
        self.assertEqual(report.valid_uom_rate, 1.0)
        self.assertGreater(report.quality_score, 0.70)
        self.assertTrue(report.is_acceptable)

    def test_verhoeff_cnmc_validation(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.scalar.return_value = 1042

        code = CNMCMinter.mint_distributed_cnmc(mock_db, golden_record_id=1, sector="OIL_AND_GAS", category_code="4014")
        self.assertTrue(code.startswith("CNMC-OG-4014-"))
        self.assertTrue(validate_verhoeff(code))

    def test_active_learning_triplets(self):
        triplets = [
            {"anchor": "GATE VALVE 2IN 300#", "positive": "2\" GATE VLV CL300 WCB", "negative": None},
            {"anchor": "GATE VALVE 2IN 300#", "positive": None, "negative": "GATE VALVE 2IN 150#"}
        ]
        mnrl = ActiveLearningPipeline.format_mnrl_dataset(triplets)
        self.assertEqual(len(mnrl), 1)
        self.assertEqual(mnrl[0][0], "GATE VALVE 2IN 300#")
        self.assertEqual(mnrl[0][1], "2\" GATE VLV CL300 WCB")
        self.assertEqual(mnrl[0][2], "GATE VALVE 2IN 150#")

    def test_iso8000_golden_record_synthesis(self):
        class MockMat:
            def __init__(self, noun, size, rating, moc, end, base_uom="EA"):
                self.item_noun = noun
                self.nominal_size = size
                self.pressure_class = rating
                self.moc = moc
                self.schedule = None
                self.end_connection = end
                self.standard_spec = "ASME B16.34"
                self.base_uom = base_uom

        mats = [
            MockMat("VALVE, GATE", "6 INCH (150 MM)", "CLASS 300#", "ASTM A216 WCB", "FLANGED RF"),
            MockMat("VALVE, GATE", "6 INCH (150 MM)", "CLASS 300#", "ASTM A216 WCB", "FLANGED RF")
        ]
        synth = GoldenRecordService.synthesize_iso8000_description(mats)
        self.assertEqual(synth["item_noun"], "VALVE, GATE")
        self.assertIn("6 INCH (150 MM)", synth["standardized_description"])
        self.assertIn("CLASS 300#", synth["standardized_description"])
        self.assertIn("ASTM A216 WCB", synth["standardized_description"])

if __name__ == "__main__":
    unittest.main()
