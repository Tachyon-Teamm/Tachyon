import pytest
from app.services.matching.scorer import CompositeScorer

def test_cosine_similarity():
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    assert CompositeScorer.calculate_cosine_similarity(vec_a, vec_b) == 1.0

    vec_c = [0.0, 1.0, 0.0]
    assert CompositeScorer.calculate_cosine_similarity(vec_a, vec_c) == 0.0

def test_attribute_overlap_identical():
    specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#"}
    specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#"}
    overlap = CompositeScorer.calculate_attribute_overlap(specs_a, specs_b)
    assert overlap == 1.0

def test_composite_scoring_tiers():
    vec_a = [1.0, 0.5, 0.2]
    vec_b = [1.0, 0.5, 0.2]
    specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
    specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH", "pressure_class": "CLASS 300#", "moc": "WCB"}
    proc_a = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10000.0, "hsn_code": "84818030"}
    proc_b = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10500.0, "hsn_code": "84818030"}

    res = CompositeScorer.compute_composite(vec_a, vec_b, specs_a, specs_b, proc_a, proc_b)
    assert res["composite_score"] >= 0.90
    assert res["confidence_tier"] == "HIGH"
