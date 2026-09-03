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
from app.services.matching.embeddings import EmbeddingService
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

    def test_chunk2_two_pass_synonym_mapping(self):
        from app.api.v1.ingestion import STANDARD_HEADER_SYNONYMS
        import re

        test_columns = [
            ("MATERIAL_NO", "material_code"),
            ("MATNR", "material_code"),
            ("MATERIAL_NUMBER", "material_code"),
            ("ITEM_SPEC", "short_description"),
            ("MAKTX", "short_description"),
            ("SHORT_TEXT", "short_description"),
            ("UNIT_OF_MEASURE", "uom"),
            ("MEINS", "uom"),
            ("PURCHASE_ORDER_UNIT", "uom"),
            ("LAST_PO_PRICE", "base_price"),
            ("NETPR", "base_price"),
            ("UNIT_PRICE", "base_price"),  # Must map to base_price, NOT uom
            ("VENDOR_NAME", "vendor_name"),
            ("NAME1", "vendor_name"),
            ("HSN_CODE", "hsn_code"),      # Must map to hsn_code, NOT material_code
            ("SAC_CODE", "hsn_code"),
            ("TAX_CODE", "hsn_code"),
        ]

        columns = [c[0] for c in test_columns]
        suggested = {}

        # Pass 1: Strict Exact Match
        for col in columns:
            col_clean = re.sub(r'[^A-Z0-9]', '_', str(col).strip().upper())
            col_clean = re.sub(r'_+', '_', col_clean).strip('_')
            matched = False
            for target_field, synonyms in STANDARD_HEADER_SYNONYMS.items():
                for syn in synonyms:
                    syn_clean = re.sub(r'[^A-Z0-9]', '_', syn.upper()).strip('_')
                    if col_clean == syn_clean or str(col).strip().upper() == syn:
                        suggested[col] = target_field
                        matched = True
                        break
                if matched:
                    break

        # Pass 2: Word-Boundary Regex
        category_order = ["hsn_code", "base_price", "vendor_name", "short_description", "uom", "material_code"]
        for col in columns:
            if col in suggested:
                continue
            col_upper = str(col).strip().upper()
            matched = False
            for target_field in category_order:
                synonyms = STANDARD_HEADER_SYNONYMS[target_field]
                for syn in synonyms:
                    pattern = r'\b' + re.escape(syn.upper()) + r'\b'
                    if re.search(pattern, col_upper):
                        suggested[col] = target_field
                        matched = True
                        break
                if matched:
                    break

        for col_name, expected_target in test_columns:
            self.assertEqual(
                suggested.get(col_name), 
                expected_target, 
                f"Column '{col_name}' was mapped to '{suggested.get(col_name)}', expected '{expected_target}'"
            )

    def test_chunk2_price_sanitizer(self):
        from app.tasks.ingestion_tasks import sanitize_price
        self.assertEqual(sanitize_price("12500.0"), 12500.0)
        self.assertEqual(sanitize_price("12,500.00"), 12500.0)
        self.assertEqual(sanitize_price("₹ 10,800.50"), 10800.5)
        self.assertEqual(sanitize_price("$450.00"), 450.0)
        self.assertEqual(sanitize_price(""), 0.0)
        self.assertEqual(sanitize_price("N/A"), 0.0)
        self.assertEqual(sanitize_price(None), 0.0)

    def test_chunk5_canonical_synthesis_and_embedding(self):
        from app.core.config import settings
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

        # Embedding generation and unit length
        vec = EmbeddingService.generate_embedding(canon_cpcl)
        self.assertEqual(len(vec), settings.EMBEDDING_DIMENSION)
        import math
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

        # Batch generation
        batch_vecs = EmbeddingService.generate_batch_embeddings([canon_cpcl, canon_iocl, canon_bpcl])
        self.assertEqual(len(batch_vecs), 3)

        # Fallback cross-CPSE similarity
        v_cpcl = EmbeddingService._deterministic_hash_vector(canon_cpcl, settings.EMBEDDING_DIMENSION)
        v_iocl = EmbeddingService._deterministic_hash_vector(canon_iocl, settings.EMBEDDING_DIMENSION)
        sim = CompositeScorer.calculate_cosine_similarity(v_cpcl, v_iocl)
        self.assertGreaterEqual(sim, 0.90)

    def test_chunk5_dual_adaptive_scorer_rebalancing(self):
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

    def test_chunk6_guardrail_canonicalization_and_clearance(self):
        # Clearance None vs STD equivalence
        specs_a = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": None}
        specs_b = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": "STD"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

        # Voltage whitespace tolerance ("415 V" vs "415V")
        specs_v1 = {"item_noun": "SWITCHGEAR", "voltage_rating": "415 V"}
        specs_v2 = {"item_noun": "SWITCHGEAR", "voltage_rating": "415V"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_v1, specs_v2)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

        # Pressure format canonicalization ("300#" vs "CLASS 300#")
        specs_p1 = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "300#"}
        specs_p2 = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "CLASS 300#"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_p1, specs_p2)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

    def test_chunk6_dsu_cluster_safety_veto_exclusion(self):
        # Candidate edges where (1, 2) is compatible and (2, 3) is a vetoed schedule mismatch
        edges = [
            {"material_a_id": 1, "material_b_id": 2, "composite_score": 0.94, "is_vetoed": False},
            {"material_a_id": 2, "material_b_id": 3, "composite_score": 0.0, "is_vetoed": True}
        ]
        res = ClusterEngine.form_clusters(edges, min_score=0.70)
        # Material 1 and 2 should be in the same cluster
        self.assertEqual(res["material_to_cluster"].get(1), res["material_to_cluster"].get(2))
        # Material 3 must NOT be in the cluster
        self.assertNotIn(3, res["material_to_cluster"])

if __name__ == "__main__":
    unittest.main()
