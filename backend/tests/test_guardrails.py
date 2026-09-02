import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.matching.guardrails import SafetyGuardrails

class TestSafetyGuardrails(unittest.TestCase):
    def test_pressure_mismatch_veto(self):
        specs_150 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 150#"}
        specs_300 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 300#"}
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_150, specs_300)
        self.assertTrue(is_vetoed)
        self.assertIn("Pressure rating conflict", reason)
        self.assertEqual(route, "SUBSTITUTE")

    def test_pressure_canonical_format_passes(self):
        # "300#" vs "CLASS 300#" should normalize to the same pressure rating
        specs_a = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "300#"}
        specs_b = {"item_noun": "VALVE, GATE", "nominal_size": "6 INCH (150 MM)", "pressure_class": "CLASS 300#"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

    def test_schedule_mismatch_veto(self):
        specs_sch40 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 40"}
        specs_sch80 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 80"}
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_sch40, specs_sch80)
        self.assertTrue(is_vetoed)
        self.assertIn("Wall thickness schedule mismatch", reason)
        self.assertEqual(route, "SUBSTITUTE")

    def test_assembly_vs_spare_veto(self):
        specs_kit = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": True}
        specs_spare = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": False}
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_kit, specs_spare)
        self.assertTrue(is_vetoed)
        self.assertIn("Assembly Token Veto", reason)
        self.assertEqual(route, "REJECT")

    def test_bearing_clearance_std_equivalence(self):
        # None vs "STD" should evaluate as equivalent standard clearances without veto
        specs_a = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": None}
        specs_b = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": "STD"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

    def test_bearing_clearance_c3_substitute_veto(self):
        # Standard vs C3 clearance should trigger SUBSTITUTE veto
        specs_a = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": "STD"}
        specs_b = {"item_noun": "BEARING", "clean_part_number": "6205", "clearance_suffix": "C3"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertTrue(is_vetoed)
        self.assertIn("Bearing Clearance Modifier Difference", reason)
        self.assertEqual(route, "SUBSTITUTE")

    def test_voltage_whitespace_tolerance(self):
        # "415 V" vs "415V" should match without whitespace veto
        specs_a = {"item_noun": "SWITCHGEAR", "voltage_rating": "415 V"}
        specs_b = {"item_noun": "SWITCHGEAR", "voltage_rating": "415V"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed)
        self.assertEqual(route, "IDENTICAL")

    def test_voltage_mismatch_veto(self):
        # 415V vs 11KV should trigger REJECT veto
        specs_a = {"item_noun": "SWITCHGEAR", "voltage_rating": "415V"}
        specs_b = {"item_noun": "SWITCHGEAR", "voltage_rating": "11KV"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertTrue(is_vetoed)
        self.assertIn("Voltage rating conflict", reason)
        self.assertEqual(route, "REJECT")

    def test_metallurgy_mismatch_veto(self):
        # Carbon Steel vs Stainless Steel 316 should trigger SUBSTITUTE veto
        specs_a = {"item_noun": "PIPE", "moc": "CARBON STEEL A106"}
        specs_b = {"item_noun": "PIPE", "moc": "STAINLESS STEEL 316"}
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertTrue(is_vetoed)
        self.assertIn("Metallurgy Incompatibility", reason)
        self.assertEqual(route, "SUBSTITUTE")

    def test_compatible_pair_passes(self):
        specs_a = {
            "item_noun": "VALVE, GATE",
            "nominal_size": "6 INCH (150 MM)",
            "pressure_class": "CLASS 300#",
            "moc": "ASTM A216 WCB",
            "is_kit_or_assembly": False
        }
        specs_b = {
            "item_noun": "VALVE, GATE",
            "nominal_size": "6 INCH (150 MM)",
            "pressure_class": "CLASS 300#",
            "moc": "ASTM A216 WCB",
            "is_kit_or_assembly": False
        }
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
        self.assertFalse(is_vetoed)
        self.assertIsNone(reason)
        self.assertEqual(route, "IDENTICAL")

if __name__ == "__main__":
    unittest.main()

