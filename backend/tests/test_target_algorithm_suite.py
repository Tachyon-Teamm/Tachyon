import pytest
from app.services.matching.embeddings import EmbeddingService
from app.services.matching.scorer import CompositeScorer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.cluster_engine import ClusterEngine
from app.services.governance.cnmc_minter import CNMCMinter, validate_verhoeff
from app.services.governance.golden_record_service import GoldenRecordService
from app.tasks.active_learning import ActiveLearningPipeline
from app.services.normalization.data_profiler import DataProfiler

class TestTargetAlgorithmSuite:
    def test_1_bge_m3_1024d_and_sparse_splade(self):
        desc = "VALVE GATE 2IN 300# WCB FLG RF ASME B16.34"
        dense_vec = EmbeddingService.generate_embedding(desc)
        assert len(dense_vec) == 1024
        
        sparse_vec = EmbeddingService.generate_sparse_vector(desc)
        assert "300#" in sparse_vec or "300" in sparse_vec
        assert "WCB" in sparse_vec
        assert "GATE" in sparse_vec
        assert "VALVE" in sparse_vec

    def test_2_reciprocal_rank_fusion(self):
        dense_scores = {101: 0.95, 102: 0.88, 103: 0.72}
        sparse_scores = {102: 0.99, 101: 0.70, 104: 0.80}
        
        rrf = EmbeddingService.compute_reciprocal_rank_fusion(dense_scores, sparse_scores, k=60)
        # Both 101 and 102 appear at top ranks across dense and sparse
        assert 101 in rrf and 102 in rrf
        assert rrf[101] > 0 and rrf[102] > 0

    def test_3_correlation_clustering_pivot(self):
        # Nodes 1, 2, 3 are identical gate valves across IOCL, CPCL, BPCL
        # Node 4 is a ball valve (negative edge to 1,2,3)
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
        # Should create 2 distinct clusters: {1, 2, 3} and {4}
        cluster_lens = sorted([len(v) for v in clusters.values()])
        assert cluster_lens == [1, 3]

    def test_4_multi_sector_safety_guardrails(self):
        # Steel rebar grade mismatch Fe 500D vs Fe 550D
        spec_a = {"item_noun": "STEEL REBAR", "steel_grade": "FE 500D"}
        spec_b = {"item_noun": "STEEL REBAR", "steel_grade": "FE 550D"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(spec_a, spec_b)
        assert vetoed is True
        assert "Structural Safety Veto" in reason

        # Mining conveyor belt width mismatch
        mining_a = {"item_noun": "CONVEYOR BELTING", "belt_width": "1200 MM"}
        mining_b = {"item_noun": "CONVEYOR BELTING", "belt_width": "1400 MM"}
        vetoed, reason, route = SafetyGuardrails.evaluate_pair(mining_a, mining_b)
        assert vetoed is True
        assert "Mining Safety Veto" in reason

    def test_5_distributed_cnmc_minter_and_verhoeff(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.scalar.return_value = 1042
        
        code = CNMCMinter.mint_distributed_cnmc(mock_db, golden_record_id=1, sector="OIL_AND_GAS", category_code="4014")
        assert code.startswith("CNMC-OG-4014-")
        # Check Verhoeff checksum validation
        assert validate_verhoeff(code) is True

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
        assert res["item_noun"] == "CONVEYOR BELTING"
        assert "1200 MM" in res["standardized_description"]
        assert "1000 N/MM" in res["standardized_description"]
        assert res["technical_attributes"]["belt_width"] == "1200 MM"

    def test_7_shannon_entropy_data_profiler(self):
        records = [
            {"material_code": "M001", "short_description": "VALVE GATE 2 INCH 300# WCB FLG RF ASME B16.34", "uom": "EA"},
            {"material_code": "M002", "short_description": "PIPE SEAMLESS 4 INCH SCH 40 CARBON STEEL ASTM A106", "uom": "MTR"},
            {"material_code": "M003", "short_description": "BEARING DEEP GROOVE BALL 6205-2RS1 C3 SKF", "uom": "NOS"},
            {"material_code": "M004", "short_description": "HIGH ALUMINA REFRACTORY FIREBRICK 70% AL2O3 1450 DEG C", "uom": "PCS"},
        ]
        report = DataProfiler.profile_records(records)
        assert report.completeness_rate == 1.0
        assert report.valid_uom_rate == 1.0
        assert report.shannon_entropy > 0.3
        assert report.is_acceptable is True

    def test_8_active_learning_triplet_formatter(self):
        triplets = [
            {"anchor": "GATE VALVE 2IN 300#", "positive": "2\" GATE VLV CL300 WCB", "negative": None},
            {"anchor": "GATE VALVE 2IN 300#", "positive": None, "negative": "GATE VALVE 2IN 150#"}
        ]
        mnrl = ActiveLearningPipeline.format_mnrl_dataset(triplets)
        assert len(mnrl) == 1
        assert mnrl[0][0] == "GATE VALVE 2IN 300#"
        assert mnrl[0][1] == "2\" GATE VLV CL300 WCB"
        assert mnrl[0][2] == "GATE VALVE 2IN 150#"
