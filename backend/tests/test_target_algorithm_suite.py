import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.matching.embeddings import EmbeddingService
from app.services.matching.scorer import CompositeScorer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.cluster_engine import ClusterEngine
from app.services.governance.cnmc_minter import CNMCMinter, validate_verhoeff
from app.services.governance.golden_record_service import GoldenRecordService
from app.tasks.active_learning import ActiveLearningPipeline
from app.services.normalization.data_profiler import DataProfiler

class TestTargetAlgorithmSuite(unittest.TestCase):
    def test_1_bge_m3_1024d_and_sparse_splade(self):
        desc = "VALVE GATE 2IN 300# WCB FLG RF ASME B16.34"
        from app.core.config import settings
        dense_vec = EmbeddingService.generate_embedding(desc)
        self.assertEqual(len(dense_vec), settings.EMBEDDING_DIMENSION)
        
        dense_1024 = EmbeddingService._deterministic_hash_vector(desc, 1024)
        self.assertEqual(len(dense_1024), 1024)
        
        sparse_vec = EmbeddingService.generate_sparse_vector(desc)
        self.assertTrue("300#" in sparse_vec or "300" in sparse_vec)
        self.assertIn("WCB", sparse_vec)
        self.assertIn("GATE", sparse_vec)
        self.assertIn("VALVE", sparse_vec)

    def test_2_reciprocal_rank_fusion(self):
        dense_scores = {101: 0.95, 102: 0.88, 103: 0.72}
        sparse_scores = {102: 0.99, 101: 0.70, 104: 0.80}
        
        rrf = EmbeddingService.compute_reciprocal_rank_fusion(dense_scores, sparse_scores, k=60)
        self.assertIn(101, rrf)
        self.assertIn(102, rrf)
        self.assertGreater(rrf[101], 0)
        self.assertGreater(rrf[102], 0)

    def test_3_correlation_clustering_pivot(self):
        nodes = [1, 2, 3, 4]
        positive_edges = {
            (1, 2): 0.94,
            (1, 3): 0.92,
            (2, 3): 0.96
        }
        negative_edges = {(1, 4), (2, 4), (3, 4)}
        
        clusters = ClusterEngine.correlation_clustering_pivot(
            nodes=nodes,
            positive_edges=positive_edges,
            negative_edges=negative_edges,
            threshold=0.70
        )
        cluster_lens = sorted([len(v) for v in clusters.values()])
        self.assertEqual(cluster_lens, [1, 3])

    def test_4_multi_sector_safety_guardrails(self):
        # Steel rebar grade mismatch Fe 500D vs Fe 550D
        spec_a = {"item_noun": "STEEL REBAR", "steel_grade": "FE 500D"}
        spec_b = {"item_noun": "STEEL REBAR", "steel_grade": "FE 550D"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(spec_a, spec_b)
        self.assertTrue(vetoed)
        self.assertIn("Structural Safety Veto", reason)

        # Mining conveyor belt width mismatch
        mining_a = {"item_noun": "CONVEYOR BELTING", "belt_width": "1200 MM"}
        mining_b = {"item_noun": "CONVEYOR BELTING", "belt_width": "1400 MM"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(mining_a, mining_b)
        self.assertTrue(vetoed)
        self.assertIn("Mining Safety Veto", reason)

    def test_5_distributed_cnmc_minter_and_verhoeff(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.scalar.return_value = 1042
        
        code = CNMCMinter.mint_distributed_cnmc(mock_db, golden_record_id=1, sector="OIL_AND_GAS", category_code="4014")
        self.assertTrue(code.startswith("CNMC-OG-4014-"))
        self.assertTrue(validate_verhoeff(code))

    def test_6_multi_sector_golden_record_synthesis(self):
        class MockMat:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
                    
        m1 = MockMat(
            item_noun="CONVEYOR BELTING",
            base_uom="MTR",
            extracted_attributes={"belt_width": "1200 MM", "tensile_rating": "1000 N/MM"}
        )
        m2 = MockMat(
            item_noun="CONVEYOR BELTING",
            base_uom="MTR",
            extracted_attributes={"belt_width": "1200 MM", "tensile_rating": "1000 N/MM"}
        )
        
        res = GoldenRecordService.synthesize_iso8000_description([m1, m2])
        self.assertEqual(res["item_noun"], "CONVEYOR BELTING")
        self.assertIn("1200 MM", res["standardized_description"])
        self.assertIn("1000 N/MM", res["standardized_description"])
        self.assertEqual(res["technical_attributes"]["belt_width"], "1200 MM")

    def test_7_shannon_entropy_data_profiler(self):
        records = [
            {"material_code": "M001", "short_description": "VALVE GATE 2 INCH 300# WCB FLG RF ASME B16.34", "uom": "EA"},
            {"material_code": "M002", "short_description": "PIPE SEAMLESS 4 INCH SCH 40 CARBON STEEL ASTM A106", "uom": "MTR"},
            {"material_code": "M003", "short_description": "BEARING DEEP GROOVE BALL 6205-2RS1 C3 SKF", "uom": "NOS"},
            {"material_code": "M004", "short_description": "HIGH ALUMINA REFRACTORY FIREBRICK 70% AL2O3 1450 DEG C", "uom": "PCS"},
        ]
        report = DataProfiler.profile_records(records)
        self.assertEqual(report.completeness_rate, 1.0)
        self.assertEqual(report.valid_uom_rate, 1.0)
        self.assertGreater(report.shannon_entropy, 0.3)
        self.assertTrue(report.is_acceptable)

    def test_8_active_learning_triplet_formatter(self):
        triplets = [
            {"anchor": "GATE VALVE 2IN 300#", "positive": "2\" GATE VLV CL300 WCB", "negative": None},
            {"anchor": "GATE VALVE 2IN 300#", "positive": None, "negative": "GATE VALVE 2IN 150#"}
        ]
        mnrl = ActiveLearningPipeline.format_mnrl_dataset(triplets)
        self.assertEqual(len(mnrl), 1)
        self.assertEqual(mnrl[0][0], "GATE VALVE 2IN 300#")
        self.assertEqual(mnrl[0][1], "2\" GATE VLV CL300 WCB")
        self.assertEqual(mnrl[0][2], "GATE VALVE 2IN 150#")

if __name__ == "__main__":
    unittest.main()
