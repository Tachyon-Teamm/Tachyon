import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.governance.golden_record_service import GoldenRecordService

class TestAllEightCPCLIOCLBPCLScenarios(unittest.TestCase):
    """
    Direct verification of all 8 Real-World Stress-Testing Scenarios
    specified in Section 6 of ARCHITECTURE_AND_TESTING_GUIDE.md.
    """

    def test_scenario_1_commodity_spec_variation(self):
        """Scenario 1: CPCL, IOCL, BPCL 6\" Gate Valve 300#"""
        cpcl_desc = "VLV GATE 6IN 300# CS FLG"
        iocl_desc = "VALVE, GATE, 150MM, CL300, WCB"
        bpcl_desc = "6 INCH GATE VALVE FLANGED 300#"

        specs_cpcl = SpecExtractor.extract_specs(cpcl_desc)
        specs_iocl = SpecExtractor.extract_specs(iocl_desc)
        specs_bpcl = SpecExtractor.extract_specs(bpcl_desc)

        self.assertEqual(specs_cpcl["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs_iocl["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs_bpcl["nominal_size"], "6 INCH (150 MM)")

        self.assertEqual(specs_cpcl["pressure_class"], "CLASS 300#")
        self.assertEqual(specs_iocl["pressure_class"], "CLASS 300#")
        self.assertEqual(specs_bpcl["pressure_class"], "CLASS 300#")

        # Check safety guardrail
        vetoed, reason, _ = SafetyGuardrails.evaluate_pair(specs_cpcl, specs_iocl)
        self.assertFalse(vetoed)

    def test_scenario_2_safety_critical_variations(self):
        """Scenario 2: Pipe Sch 40 vs Sch 80 & Valve 150# vs 300#"""
        # Wall thickness conflict
        sch40_specs = SpecExtractor.extract_specs("PIPE CS 4\" SCH 40 A106")
        sch80_specs = SpecExtractor.extract_specs("PIPE CS 4\" SCH 80 A106")
        vetoed_sch, reason_sch, route_sch = SafetyGuardrails.evaluate_pair(sch40_specs, sch80_specs)
        self.assertTrue(vetoed_sch)
        self.assertIn("Wall thickness schedule mismatch", reason_sch)

        # Pressure class conflict
        v150_specs = SpecExtractor.extract_specs("VALVE 2\" 150#")
        v300_specs = SpecExtractor.extract_specs("VALVE 2\" 300#")
        vetoed_p, reason_p, route_p = SafetyGuardrails.evaluate_pair(v150_specs, v300_specs)
        self.assertTrue(vetoed_p)
        self.assertIn("Pressure rating conflict", reason_p)

    def test_scenario_3_bearing_part_no_clearance(self):
        """Scenario 3: OEM Part No. & Clearance Suffixes"""
        cpcl_brg = SpecExtractor.extract_specs("BEARING 6205-2RS1 SKF")
        iocl_brg = SpecExtractor.extract_specs("SKF BEARING NO. 6205 2RS1 / C3")

        self.assertEqual(cpcl_brg["clean_part_number"], "62052RS1")
        self.assertEqual(iocl_brg["clean_part_number"], "62052RS1")
        self.assertEqual(iocl_brg["clearance_suffix"], "C3")

        vetoed, reason, route = SafetyGuardrails.evaluate_pair(cpcl_brg, iocl_brg)
        self.assertTrue(vetoed)
        self.assertEqual(route, "SUBSTITUTE")
        self.assertIn("Bearing Clearance Modifier Difference", reason)

    def test_scenario_4_vendor_alias_normalization(self):
        """Scenario 4: Petroleum Vendor Name Discrepancies"""
        v1 = VendorNormalizer.normalize_vendor("L&T VALVES LTD")
        v2 = VendorNormalizer.normalize_vendor("LARSEN & TOUBRO LTD - VALVE DIV")
        v3 = VendorNormalizer.normalize_vendor("AUDCO INDIA / L&T")

        self.assertEqual(v1, "LARSEN & TOUBRO")
        self.assertEqual(v2, "LARSEN & TOUBRO")
        self.assertEqual(v3, "LARSEN & TOUBRO")

    def test_scenario_5_assembly_vs_spare_part(self):
        """Scenario 5: Assemblies / Kits vs Component Spares"""
        kit_specs = SpecExtractor.extract_specs("MECH SEAL CARTRIDGE PUMP P-101A (SET)")
        spare_specs = SpecExtractor.extract_specs("ROTARY SEAL RING FOR PUMP P-101A")

        self.assertTrue(kit_specs["is_kit_or_assembly"])
        self.assertFalse(spare_specs["is_kit_or_assembly"])

        vetoed, reason, route = SafetyGuardrails.evaluate_pair(kit_specs, spare_specs)
        self.assertTrue(vetoed)
        self.assertIn("Assembly Token Veto", reason)
        self.assertEqual(route, "REJECT")

    def test_scenario_6_packaging_multiplier_consolidation(self):
        """Scenario 6: Packaging UOM vs Base UOM Discrepancy"""
        mult_bkt, base_bkt = UOMNormalizer.extract_packaging_factor("GREASE MOBILITH SHC 100 - 18KG BUCKET", "BKT")
        mult_kg, base_kg = UOMNormalizer.extract_packaging_factor("GREASE MOBILITH SHC 100", "KG")
        mult_drm, base_drm = UOMNormalizer.extract_packaging_factor("MOBILITH SHC 100 - 180KG DRUM", "DRM")

        self.assertEqual((mult_bkt, base_bkt), (18.0, "KG"))
        self.assertEqual((mult_kg, base_kg), (1.0, "KG"))
        self.assertEqual((mult_drm, base_drm), (180.0, "KG"))

        # Volume consolidation: 200 buckets (3,600 kg) + 8,000 kg + 50 drums (9,000 kg) = 20,600 KG
        total_kg = (200 * mult_bkt) + (8000 * mult_kg) + (50 * mult_drm)
        self.assertEqual(total_kg, 20600.0)

    def test_scenario_7_hinglish_colloquial_refinery_terms(self):
        """Scenario 7: Indian Plant Colloquial Terms (Jaali wala -> Spiral wound)"""
        raw_iocl = "4\" SPIRAL GASKET JAALI WALA"
        clean = DomainLexicon.preprocess_text(raw_iocl)
        self.assertIn("SPIRAL WOUND", clean)

        specs_iocl = SpecExtractor.extract_specs(raw_iocl)
        specs_cpcl = SpecExtractor.extract_specs("GASKET SPIRAL WOUND 4\" CS/SS")

        self.assertEqual(specs_iocl["item_noun"], "GASKET, SPIRAL WOUND")
        self.assertEqual(specs_cpcl["item_noun"], "GASKET, SPIRAL WOUND")
        self.assertEqual(specs_iocl["nominal_size"], "4 INCH (100 MM)")

    def test_scenario_8_standards_equivalence(self):
        """Scenario 8: Legacy Standards Equivalence (ANSI B16.5 == ASME B16.5)"""
        specs_ansi = SpecExtractor.extract_specs("FLANGE 6\" 300# ANSI B16.5")
        specs_asme = SpecExtractor.extract_specs("FLANGE 6\" 300# ASME B16.5")

        self.assertEqual(specs_ansi["standard_spec"], "ASME B16.5")
        self.assertEqual(specs_asme["standard_spec"], "ASME B16.5")

if __name__ == "__main__":
    unittest.main()
