import unittest
import sys
import os
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.matching.embeddings import EmbeddingService
from app.services.matching.scorer import CompositeScorer
from app.services.normalization.spec_extractor import SpecExtractor
from app.core.config import settings

class TestEmbeddingServiceChunk5(unittest.TestCase):
    """
    Dedicated test suite for Chunk 5 (Vector Encoding):
    - Canonical semantic synthesis
    - Vector shape and L2 normalization
    - Batch vectorization consistency
    - Punctuation-agnostic offline hash fallback
    - Dual adaptive weight rebalancing in CompositeScorer
    """

    def test_canonical_text_synthesis(self):
        """Verify that disparate CPSE descriptions synthesize into identical canonical semantic strings."""
        cpcl_raw = "VLV GATE 6IN 300# CS FLG"
        iocl_raw = "VALVE, GATE, 150MM, CL300, WCB"
        bpcl_raw = "6 INCH GATE VALVE FLANGED 300#"

        specs_cpcl = SpecExtractor.extract_specs(cpcl_raw)
        specs_iocl = SpecExtractor.extract_specs(iocl_raw)
        specs_bpcl = SpecExtractor.extract_specs(bpcl_raw)

        canon_cpcl = EmbeddingService.build_canonical_text(specs_cpcl, cpcl_raw)
        canon_iocl = EmbeddingService.build_canonical_text(specs_iocl, iocl_raw)
        canon_bpcl = EmbeddingService.build_canonical_text(specs_bpcl, bpcl_raw)

        self.assertIn("VALVE, GATE", canon_cpcl)
        self.assertIn("6 INCH (150 MM)", canon_cpcl)
        self.assertIn("CLASS 300#", canon_cpcl)

        self.assertIn("VALVE, GATE", canon_iocl)
        self.assertIn("6 INCH (150 MM)", canon_iocl)
        self.assertIn("CLASS 300#", canon_iocl)

        self.assertIn("VALVE, GATE", canon_bpcl)
        self.assertIn("6 INCH (150 MM)", canon_bpcl)
        self.assertIn("CLASS 300#", canon_bpcl)

    def test_embedding_dimension_and_normalization(self):
        """Verify vector dimension matches config (384) and norm is unit length (1.0)."""
        text = "VALVE, GATE, 6 INCH (150 MM), CLASS 300#, ASTM A216 WCB"
        vec = EmbeddingService.generate_embedding(text)

        self.assertEqual(len(vec), settings.EMBEDDING_DIMENSION)
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_batch_embeddings_consistency(self):
        """Verify batch generation returns the expected count and valid unit-normalized vectors."""
        texts = [
            "VALVE, GATE, 6 INCH (150 MM), CLASS 300#",
            "PIPE CS 4 INCH (100 MM) SCH 40",
            "BEARING 6205 2RS1 SKF",
            "GASKET SPIRAL WOUND 4 INCH"
        ]
        vectors = EmbeddingService.generate_batch_embeddings(texts)
        self.assertEqual(len(vectors), len(texts))
        for v in vectors:
            self.assertEqual(len(v), settings.EMBEDDING_DIMENSION)
            norm = math.sqrt(sum(x * x for x in v))
            self.assertAlmostEqual(norm, 1.0, places=4)

    def test_deterministic_fallback_punctuation_resilience(self):
        """Verify fallback hash vector ignores punctuation discrepancies (commas, quotes, hashes)."""
        v1 = EmbeddingService._deterministic_hash_vector("VALVE, GATE, 6 INCH, CLASS 300#", settings.EMBEDDING_DIMENSION)
        v2 = EmbeddingService._deterministic_hash_vector("VALVE GATE 6 INCH CLASS 300", settings.EMBEDDING_DIMENSION)

        sim = CompositeScorer.calculate_cosine_similarity(v1, v2)
        self.assertGreaterEqual(sim, 0.85)

    def test_deterministic_fallback_cross_cpse_similarity(self):
        """Verify canonical strings from CPCL and IOCL yield high cosine similarity in fallback mode."""
        canon_cpcl = "VALVE, GATE, 6 INCH (150 MM), CLASS 300#, ASTM A216 WCB, FLANGED RF"
        canon_iocl = "VALVE, GATE, 6 INCH (150 MM), CLASS 300#, ASTM A216 WCB"

        v_cpcl = EmbeddingService._deterministic_hash_vector(canon_cpcl, settings.EMBEDDING_DIMENSION)
        v_iocl = EmbeddingService._deterministic_hash_vector(canon_iocl, settings.EMBEDDING_DIMENSION)

        sim = CompositeScorer.calculate_cosine_similarity(v_cpcl, v_iocl)
        self.assertGreaterEqual(sim, 0.90)

    def test_empty_and_null_inputs_safe(self):
        """Verify empty string and None inputs do not raise unhandled exceptions."""
        v_empty = EmbeddingService.generate_embedding("")
        self.assertEqual(len(v_empty), settings.EMBEDDING_DIMENSION)

        v_batch_empty = EmbeddingService.generate_batch_embeddings([])
        self.assertEqual(v_batch_empty, [])

        canon_none = EmbeddingService.build_canonical_text(None, "")
        self.assertEqual(canon_none, "")

    def test_dual_adaptive_scorer_rebalancing_when_vectors_missing(self):
        """Verify CompositeScorer rebalances semantic weight when vectors are missing, retaining matches."""
        specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "CLASS 300#"}
        specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "CLASS 300#"}
        proc_a = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10000.0, "hsn_code": "84818030"}
        proc_b = {"vendor_normalized": "LARSEN & TOUBRO", "unit_price": 10500.0, "hsn_code": "84818030"}

        # Missing vector test: vec_a and vec_b are empty
        res = CompositeScorer.compute_composite(
            vec_a=[],
            vec_b=[],
            specs_a=specs_a,
            specs_b=specs_b,
            proc_a=proc_a,
            proc_b=proc_b,
            category="VALVE"
        )

        self.assertGreaterEqual(res["composite_score"], 0.85)
        self.assertIn(res["confidence_tier"], ["HIGH", "MEDIUM"])
        self.assertGreaterEqual(res["weights"]["attribute"], 0.50)

if __name__ == "__main__":
    unittest.main()
