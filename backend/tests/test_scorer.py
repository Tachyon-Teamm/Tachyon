import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.matching.scorer import CompositeScorer

class TestScorer(unittest.TestCase):
    def test_cosine_similarity(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]
        self.assertEqual(CompositeScorer.calculate_cosine_similarity(vec_a, vec_b), 1.0)

        vec_c = [0.0, 1.0, 0.0]
        self.assertEqual(CompositeScorer.calculate_cosine_similarity(vec_a, vec_c), 0.0)

    def test_attribute_overlap_identical(self):
        specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#"}
        specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#"}
        overlap = CompositeScorer.calculate_attribute_overlap(specs_a, specs_b)
        self.assertEqual(overlap, 1.0)

    def test_composite_scoring_tiers(self):
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

if __name__ == "__main__":
    unittest.main()
