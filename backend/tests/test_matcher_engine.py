import unittest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.models import (
    Base, CPSE, Material, MaterialEmbedding, ProcurementHistory,
    MatchJob, MatchCandidate, ReviewQueue
)
from app.services.matching.matcher_engine import MatcherEngine
from app.services.matching.cluster_engine import ClusterEngine

class TestMatcherEngine(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for isolated unit testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed CPSEs
        self.cpcl = CPSE(id=1, code="CPCL", name="Chennai Petroleum Corp Ltd")
        self.iocl = CPSE(id=2, code="IOCL", name="Indian Oil Corp Ltd")
        self.bpcl = CPSE(id=3, code="BPCL", name="Bharat Petroleum Corp Ltd")
        self.db.add_all([self.cpcl, self.iocl, self.bpcl])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_cross_cpse_filter_skips_same_cpse_pairs(self):
        # Two distinct materials from the SAME CPSE (IOCL)
        m1 = Material(
            id=1, cpse_id=2, material_code="IOCL-101",
            short_description="VALVE, GATE, 6 INCH (150 MM), CLASS 300#, WCB",
            item_noun="VALVE, GATE", nominal_size="6 INCH (150 MM)", pressure_class="CLASS 300#",
            moc="ASTM A216 WCB", status="ACTIVE"
        )
        m2 = Material(
            id=2, cpse_id=2, material_code="IOCL-102",
            short_description="VALVE, GATE, 6 INCH (150 MM), CLASS 300#, WCB",
            item_noun="VALVE, GATE", nominal_size="6 INCH (150 MM)", pressure_class="CLASS 300#",
            moc="ASTM A216 WCB", status="ACTIVE"
        )
        self.db.add_all([m1, m2])
        self.db.commit()

        job = MatchJob(id=1, status="PENDING")
        self.db.add(job)
        self.db.commit()

        res = MatcherEngine.execute_cross_cpse_matching(self.db, job.id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["pairs_evaluated"], 0)
        self.assertEqual(res["candidates_found"], 0)

    def test_cross_cpse_matching_and_dsu_cluster_safety_gating(self):
        # CPCL 6" 300# Gate Valve vs IOCL 6" 300# Gate Valve (Compatible)
        m_cpcl = Material(
            id=10, cpse_id=1, material_code="CPCL-VALVE-1",
            short_description="VLV GATE 6IN 300# CS FLG",
            item_noun="VALVE, GATE", nominal_size="6 INCH (150 MM)", pressure_class="CLASS 300#",
            moc="ASTM A216 WCB", status="ACTIVE"
        )
        m_iocl = Material(
            id=20, cpse_id=2, material_code="IOCL-VALVE-1",
            short_description="VALVE, GATE, 150MM, CL300, WCB",
            item_noun="VALVE, GATE", nominal_size="6 INCH (150 MM)", pressure_class="CLASS 300#",
            moc="ASTM A216 WCB", status="ACTIVE"
        )
        # IOCL 4" SCH 40 Pipe vs BPCL 4" SCH 80 Pipe (Incompatible Veto)
        p_iocl = Material(
            id=30, cpse_id=2, material_code="IOCL-PIPE-40",
            short_description="PIPE CS 4IN SCH 40 A106",
            item_noun="PIPE", nominal_size="4 INCH (100 MM)", schedule="SCH 40",
            moc="ASTM A106", status="ACTIVE"
        )
        p_bpcl = Material(
            id=40, cpse_id=3, material_code="BPCL-PIPE-80",
            short_description="PIPE CS 4IN SCH 80 A106",
            item_noun="PIPE", nominal_size="4 INCH (100 MM)", schedule="SCH 80",
            moc="ASTM A106", status="ACTIVE"
        )
        self.db.add_all([m_cpcl, m_iocl, p_iocl, p_bpcl])
        self.db.commit()

        job = MatchJob(id=2, status="PENDING")
        self.db.add(job)
        self.db.commit()

        res = MatcherEngine.execute_cross_cpse_matching(self.db, job.id)
        self.assertEqual(res["status"], "COMPLETED")

        # Verify Candidate Pairs in DB
        candidates = self.db.query(MatchCandidate).filter(MatchCandidate.job_id == job.id).all()
        self.assertGreaterEqual(len(candidates), 2)

        valve_cand = next((c for c in candidates if c.material_a_id in (10, 20) and c.material_b_id in (10, 20)), None)
        self.assertIsNotNone(valve_cand)
        self.assertFalse(valve_cand.safety_veto)
        self.assertEqual(valve_cand.suggested_route, "IDENTICAL")

        pipe_cand = next((c for c in candidates if c.material_a_id in (30, 40) and c.material_b_id in (30, 40)), None)
        self.assertIsNotNone(pipe_cand)
        self.assertTrue(pipe_cand.safety_veto)
        self.assertEqual(pipe_cand.suggested_route, "SUBSTITUTE")
        self.assertEqual(pipe_cand.confidence_tier, "MEDIUM")

        # Verify that pipe pair does NOT share the identical cluster_group_id of the valve pair
        self.assertNotEqual(valve_cand.cluster_group_id, pipe_cand.cluster_group_id)

    def test_fault_isolation_on_malformed_record(self):
        # Material with valid attributes
        m_good_1 = Material(
            id=101, cpse_id=1, material_code="GOOD-1",
            short_description="PIPE CS 2IN SCH 40",
            item_noun="PIPE", nominal_size="2 INCH (50 MM)", schedule="SCH 40", status="ACTIVE"
        )
        m_good_2 = Material(
            id=102, cpse_id=2, material_code="GOOD-2",
            short_description="PIPE CS 2IN SCH 40",
            item_noun="PIPE", nominal_size="2 INCH (50 MM)", schedule="SCH 40", status="ACTIVE"
        )
        self.db.add_all([m_good_1, m_good_2])
        self.db.commit()

        job = MatchJob(id=3, status="PENDING")
        self.db.add(job)
        self.db.commit()

        # Job should complete successfully
        res = MatcherEngine.execute_cross_cpse_matching(self.db, job.id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["candidates_found"], 1)

if __name__ == "__main__":
    unittest.main()
