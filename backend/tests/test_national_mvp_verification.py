import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.matching.embeddings import EmbeddingService
from app.services.matching.scorer import CompositeScorer
from app.services.normalization.spec_extractor import SpecExtractor
from app.schemas.schemas import DemandSavingsItem, QualityHeatmapItem, VennOverlapData

class TestNationalMVPVerification(unittest.TestCase):
    """
    Verifies all requirements of the National Unified Material Master MVP:
    - Real BM25 lexical token scoring
    - Dynamic Multi-CPSE schemas and analytics
    - Contextual metallurgy without casting bias
    - Dynamic taxonomy resolution
    """

    def test_1_bm25_pairwise_similarity_part_numbers(self):
        """Verify real BM25 pairwise similarity scores identical/near-identical technical codes high."""
        desc_a = "BALL BEARING 6205-2RS1 SKF DEEP GROOVE"
        desc_b = "DEEP GROOVE BALL BEARING 6205-2RS1 SKF C3"
        desc_c = "GATE VALVE 6 INCH 300# FLANGED WCB"

        sim_match = EmbeddingService.compute_bm25_pairwise_similarity(desc_a, desc_b)
        sim_diff = EmbeddingService.compute_bm25_pairwise_similarity(desc_a, desc_c)

        self.assertGreater(sim_match, 0.60, f"Expected high BM25 score for matching bearing part number, got {sim_match}")
        self.assertEqual(sim_diff, 0.0, f"Expected 0.0 BM25 score for disjoint bearing vs valve, got {sim_diff}")
        self.assertLessEqual(sim_match, 1.0)

    def test_2_dynamic_multi_cpse_demand_item(self):
        """Verify DemandSavingsItem handles dynamic CPSE volumes beyond CPCL, IOCL, BPCL."""
        item = DemandSavingsItem(
            cnmc_code="CNMC-OIL-401416-0001",
            material_description="GATE VALVE 6 INCH 300#",
            organization_volumes={
                "CPCL": 120.0,
                "IOCL": 450.0,
                "BPCL": 310.0,
                "NTPC": 200.0,
                "SAIL": 150.0
            },
            total_volume=1230.0,
            base_uom="EA",
            avg_price=12500.0,
            max_price=14000.0,
            min_price=11000.0,
            estimated_savings_lakhs=36.9
        )
        self.assertEqual(item.organization_volumes["NTPC"], 200.0)
        self.assertEqual(item.organization_volumes["SAIL"], 150.0)
        self.assertEqual(item.total_volume, 1230.0)

    def test_3_dynamic_heatmap_and_venn_overlap(self):
        """Verify QualityHeatmapItem and VennOverlapData support arbitrary N-enterprise metrics."""
        heatmap = QualityHeatmapItem(
            field_name="MOC / Metallurgy",
            cpse_scores={"CPCL": 94.2, "IOCL": 88.5, "BPCL": 91.0, "ONGC": 96.0, "GAIL": 89.4}
        )
        self.assertEqual(heatmap.cpse_scores["ONGC"], 96.0)
        self.assertEqual(heatmap.cpse_scores["GAIL"], 89.4)

        venn = VennOverlapData(
            cpcl_only=10,
            iocl_only=15,
            bpcl_only=12,
            cpcl_iocl=25,
            iocl_bpcl=18,
            cpcl_bpcl=14,
            all_three=42,
            total_clusters=126,
            multi_cpse_clusters=99,
            pairwise_overlap={"CPCL_IOCL": 25, "IOCL_BPCL": 18, "NTPC_SAIL": 14},
            organization_counts={"CPCL": 91, "IOCL": 100, "BPCL": 86, "NTPC": 14}
        )
        self.assertEqual(venn.multi_cpse_clusters, 99)
        self.assertEqual(venn.pairwise_overlap["NTPC_SAIL"], 14)

    def test_4_contextual_metallurgy_no_casting_bias(self):
        """Verify CS metallurgy assigns ASTM A105 to flanges, A106 to pipes, A216 to valves, and Carbon Steel to general."""
        specs_flange = SpecExtractor.extract_specs("FLANGE WNRF 4 INCH 300# CS")
        specs_pipe = SpecExtractor.extract_specs("PIPE CS 6 INCH SCH 40")
        specs_valve = SpecExtractor.extract_specs("VALVE GATE 2 INCH 150# CS")
        specs_gen = SpecExtractor.extract_specs("FASTENER HEX BOLT M16 X 65 CS")

        self.assertEqual(specs_flange.get("moc"), "ASTM A105", f"Flange CS should be A105, got {specs_flange.get('moc')}")
        self.assertEqual(specs_pipe.get("moc"), "ASTM A106 GR.B", f"Pipe CS should be A106, got {specs_pipe.get('moc')}")
        self.assertEqual(specs_valve.get("moc"), "ASTM A216 WCB", f"Valve CS should be A216 WCB, got {specs_valve.get('moc')}")
        self.assertEqual(specs_gen.get("moc"), "CARBON STEEL", f"General CS should be CARBON STEEL, got {specs_gen.get('moc')}")

    def test_5_scorer_dynamic_weight_redistribution(self):
        """Verify scorer adaptively redistributes weights when specs are absent without injecting fake scores."""
        # Pair with descriptions but no extracted specs
        res = CompositeScorer.compute_composite(
            vec_a=[0.1] * 768,
            vec_b=[0.1] * 768,
            specs_a={},
            specs_b={},
            desc_a="GENERIC SPARE ITEM A",
            desc_b="GENERIC SPARE ITEM B",
            proc_a={},
            proc_b={}
        )
        self.assertIn("composite_score", res)
        self.assertGreater(res["weights"]["semantic"], 0.0)
        self.assertGreater(res["weights"]["sparse"], 0.0)
        # Attribute weight should be 0 because specs are empty
        self.assertEqual(res["weights"]["attribute"], 0.0)
        # Weights should sum to 1.0
        total_w = sum(res["weights"].values())
        self.assertAlmostEqual(total_w, 1.0, places=3)

    def test_6_demand_aggregation_live_price_variance(self):
        """Verify DashboardService.get_demand_aggregation_table computes live price variance and volume savings."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.models import Base, CPSE, Material, CNMCCode, GoldenRecord, Crosswalk, ProcurementHistory
        from app.services.analytics.dashboard_service import DashboardService

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            cpcl = CPSE(id=1, code="CPCL", name="CPCL", is_active=True)
            iocl = CPSE(id=2, code="IOCL", name="IOCL", is_active=True)
            db.add_all([cpcl, iocl])
            db.flush()

            m1 = Material(id=1, cpse_id=1, material_code="CPCL-V1", short_description="GATE VALVE 2 INCH 150#", package_multiplier=1.0, status="ACTIVE")
            m2 = Material(id=2, cpse_id=2, material_code="IOCL-V1", short_description="GATE VALVE 2 INCH 150#", package_multiplier=1.0, status="ACTIVE")
            db.add_all([m1, m2])
            db.flush()

            p1 = ProcurementHistory(material_id=1, cpse_id=1, unit_price=10000.0, quantity=50.0)
            p2 = ProcurementHistory(material_id=2, cpse_id=2, unit_price=15000.0, quantity=100.0)
            db.add_all([p1, p2])
            db.flush()

            golden = GoldenRecord(id=1, standardized_description="GATE VALVE 2 INCH 150# WCB", item_noun="VALVE, GATE", base_uom="EA")
            db.add(golden)
            db.flush()

            cnmc = CNMCCode(id=1, code="CNMC-OIL-401416-0001", golden_record_id=golden.id)
            db.add(cnmc)
            db.flush()

            cw1 = Crosswalk(cnmc_id=1, cpse_id=1, material_id=1, local_material_code="CPCL-V1", mapping_type="IDENTICAL", is_active=True)
            cw2 = Crosswalk(cnmc_id=1, cpse_id=2, material_id=2, local_material_code="IOCL-V1", mapping_type="IDENTICAL", is_active=True)
            db.add_all([cw1, cw2])
            db.commit()

            rows = DashboardService.get_demand_aggregation_table(db)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["cnmc_code"], "CNMC-OIL-401416-0001")
            self.assertEqual(row["min_price"], 10000.0)
            self.assertEqual(row["max_price"], 15000.0)
            self.assertEqual(row["avg_price"], 12500.0)
            # Savings: (15000 - 10000) * 100 = 500,000 INR = 5.0 Lakhs
            self.assertEqual(row["estimated_savings_lakhs"], 5.0)
        finally:
            db.close()
            Base.metadata.drop_all(engine)

    def test_7_review_partial_approval_requeue_and_split(self):
        """Verify partial cluster approval re-queues unselected items and SPLIT separates them."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from unittest.mock import MagicMock, patch
        from app.models.models import (
            Base, CPSE, Material, ReviewQueue, MatchCandidate, GoldenRecord,
            CNMCCode, Crosswalk, AuditLog, ReviewFeedback, MatchJob
        )
        from app.schemas.schemas import ReviewActionRequest
        from app.api.v1.review import execute_review_action
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            # Seed CPSEs
            cpcl = CPSE(id=1, code="CPCL", name="CPCL", is_active=True)
            iocl = CPSE(id=2, code="IOCL", name="IOCL", is_active=True)
            db.add_all([cpcl, iocl])
            db.flush()

            # Seed 4 materials
            m1 = Material(id=1, cpse_id=1, material_code="M-1", short_description="BALL VALVE 2 INCH 150#", item_noun="VALVE, BALL", status="ACTIVE")
            m2 = Material(id=2, cpse_id=2, material_code="M-2", short_description="BALL VALVE 2 INCH 150#", item_noun="VALVE, BALL", status="ACTIVE")
            m3 = Material(id=3, cpse_id=1, material_code="M-3", short_description="GATE VALVE 4 INCH 300#", item_noun="VALVE, GATE", status="ACTIVE")
            m4 = Material(id=4, cpse_id=2, material_code="M-4", short_description="GATE VALVE 4 INCH 300#", item_noun="VALVE, GATE", status="ACTIVE")
            db.add_all([m1, m2, m3, m4])
            db.flush()

            job = MatchJob(id=1, status="COMPLETED")
            db.add(job)
            db.flush()

            cid = "CLUST-TEST-PARTIAL"
            rq = ReviewQueue(id=1, cluster_group_id=cid, status="PENDING", confidence_tier="MEDIUM")
            db.add(rq)

            # Add candidates connecting materials
            c1 = MatchCandidate(id=1, job_id=1, cluster_group_id=cid, material_a_id=1, material_b_id=2, semantic_score=0.9, attribute_score=0.9, procurement_score=0.9, composite_score=0.9, safety_veto=False)
            c2 = MatchCandidate(id=2, job_id=1, cluster_group_id=cid, material_a_id=3, material_b_id=4, semantic_score=0.8, attribute_score=0.8, procurement_score=0.8, composite_score=0.8, safety_veto=False)
            db.add_all([c1, c2])
            db.commit()

            with patch("app.api.v1.review.get_sync_session", return_value=db):
                dummy_user = MagicMock()
                dummy_user.user_id = 999
                dummy_user.username = "steward"

                # Action: Approve only m1 and m2
                req = ReviewActionRequest(
                    cluster_group_id=cid,
                    decision_type="IDENTICAL",
                    selected_material_ids=[1, 2],
                    reviewer_notes="Approved m1 and m2 only"
                )
                res = execute_review_action(action=req, current_user=dummy_user)
                self.assertEqual(res["status"], "SUCCESS")
                self.assertIsNotNone(res["minted_cnmc"])

                # Check original review is APPROVED
                orig_rq = db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == cid).first()
                self.assertEqual(orig_rq.status, "APPROVED")

                # Check remnant review cluster was created for m3 and m4
                remnant_rq = db.query(ReviewQueue).filter(
                    ReviewQueue.cluster_group_id != cid,
                    ReviewQueue.status == "PENDING"
                ).first()
                self.assertIsNotNone(remnant_rq)
                self.assertTrue(remnant_rq.cluster_group_id.startswith("CLUST-SPLIT-"))

                # Check remnant candidate points to remnant_rq.cluster_group_id
                remnant_cand = db.query(MatchCandidate).filter(
                    MatchCandidate.material_a_id == 3,
                    MatchCandidate.material_b_id == 4
                ).first()
                self.assertEqual(remnant_cand.cluster_group_id, remnant_rq.cluster_group_id)
        finally:
            db.close()
            Base.metadata.drop_all(engine)

if __name__ == "__main__":
    unittest.main()
