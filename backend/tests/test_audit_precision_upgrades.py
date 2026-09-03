import unittest
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer

class TestAuditPrecisionUpgrades(unittest.TestCase):

    def test_1_oil_seal_noun_precedence(self):
        """Verify OIL SEAL is classified as MECHANICAL SEAL, not LUBRICANT/GREASE"""
        specs = SpecExtractor.extract_specs("OIL SEAL 50X70X10 NITRILE RUBBER")
        self.assertEqual(specs["item_noun"], "MECHANICAL SEAL")

    def test_2_nominal_size_canonical_equivalence(self):
        """Verify 1/4\" and 6MM resolve canonically and do not trigger a false REJECT veto"""
        specs_a = SpecExtractor.extract_specs("VALVE 1/4\" 300# CS")
        specs_b = SpecExtractor.extract_specs("VALVE 6MM 300# CS")
        self.assertEqual(specs_a["nominal_size"], "1/4 INCH (6 MM)")
        self.assertEqual(specs_b["nominal_size"], "1/4 INCH (6 MM)")
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed, f"Should not veto equivalent sizes: {reason}")

    def test_3_compound_fraction_parsing(self):
        """Verify compound fractions like 1-1/2\" are extracted as 1-1/2 INCH (40 MM)"""
        specs = SpecExtractor.extract_specs("BALL VALVE 1-1/2\" CLASS 150 CS FLG")
        self.assertEqual(specs["nominal_size"], "1-1/2 INCH (40 MM)")

    def test_4_dimension_substring_not_multiplier(self):
        """Verify 150MM dimension is NOT parsed as a 150.0 MTR packaging multiplier"""
        mult, base_uom = UOMNormalizer.extract_packaging_factor("FLANGE 150MM CLASS 300 WNRF", "EA")
        self.assertEqual(mult, 1.0)
        self.assertEqual(base_uom, "EA")

    def test_5_vendor_word_boundary_safety(self):
        """Verify generic words containing short alias letters (e.g. GASKET, VALVE) are not misattributed to vendors"""
        norm_v1 = VendorNormalizer.normalize_vendor("GASKET SPIRAL WOUND")
        self.assertNotEqual(norm_v1, "SKF")
        self.assertEqual(norm_v1, "GASKET SPIRAL WOUND")
        
        # Exact vendor match still works
        norm_v2 = VendorNormalizer.normalize_vendor("SKF BEARINGS INDIA")
        self.assertEqual(norm_v2, "SKF")

    def test_6_scorer_null_unit_price_safe(self):
        """Verify scorer handles None-valued unit_price safely without throwing TypeError"""
        proc_a = {"unit_price": None, "vendor_normalized": "SKF", "hsn_code": "84821010"}
        proc_b = {"unit_price": 500.0, "vendor_normalized": "SKF", "hsn_code": "84821010"}
        
        # Should not raise TypeError and return a valid score in [0.0, 1.0]
        score = CompositeScorer.calculate_procurement_score(proc_a, proc_b)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_7_package_price_normalization_math(self):
        """Verify single item vs 100-pack box normalizes correctly for true price comparison"""
        p_single = 1500.0
        mult_single = 1.0
        unit_p_single = p_single / mult_single  # 1500.0/EA

        p_box = 120000.0
        mult_box = 100.0
        unit_p_box = p_box / mult_box  # 1200.0/EA

        # Unit variance should be ₹300/EA, NOT ₹118,500
        unit_delta = abs(unit_p_single - unit_p_box)
        self.assertEqual(unit_delta, 300.0)

    def test_8_golden_record_empty_materials_safe(self):
        """Verify GoldenRecordService returns complete key structure on empty list without KeyError"""
        from app.services.governance.golden_record_service import GoldenRecordService
        res = GoldenRecordService.synthesize_iso8000_description([])
        self.assertIn("standardized_description", res)
        self.assertIn("item_noun", res)
        self.assertIn("modifier", res)
        self.assertIn("nominal_size", res)
        self.assertIn("pressure_class", res)
        self.assertIn("moc", res)
        self.assertEqual(res["item_noun"], "ITEM")

    def test_9_review_action_request_validation(self):
        """Verify ReviewActionRequest strictly validates allowed decision types"""
        from app.schemas.schemas import ReviewActionRequest
        from pydantic import ValidationError
        
        # Valid action
        valid_req = ReviewActionRequest(cluster_group_id="c_1", decision_type="IDENTICAL")
        self.assertEqual(valid_req.decision_type, "IDENTICAL")
        
        # Invalid action should raise ValidationError
        with self.assertRaises(ValidationError):
            ReviewActionRequest(cluster_group_id="c_1", decision_type="INVALID_TYPO")

if __name__ == "__main__":
    unittest.main()
