import unittest
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.governance.golden_record_service import GoldenRecordService

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

    def test_vendor_normalizer(self):
        self.assertEqual(VendorNormalizer.normalize_vendor("L&T VALVES LTD"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("LARSEN & TOUBRO LTD - VALVE DIV"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("AUDCO INDIA / L&T"), "LARSEN & TOUBRO")
        self.assertEqual(VendorNormalizer.normalize_vendor("SKF INDIA"), "SKF")

    def test_composite_scorer_math(self):
        vec_a = [1.0, 0.5, 0.2]
        vec_b = [1.0, 0.5, 0.2]
        specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
        specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
        proc_a = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10000.0, "hsn_code": "84818030"}
        proc_b = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10500.0, "hsn_code": "84818030"}

        res = CompositeScorer.compute_composite(vec_a, vec_b, specs_a, specs_b, proc_a, proc_b)
        self.assertGreaterEqual(res["composite_score"], 0.90)
        self.assertEqual(res["confidence_tier"], "HIGH")

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
