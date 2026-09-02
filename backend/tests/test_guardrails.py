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

    def test_schedule_mismatch_veto(self):
        specs_sch40 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 40"}
        specs_sch80 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 80"}
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_sch40, specs_sch80)
        self.assertTrue(is_vetoed)
        self.assertIn("Wall thickness schedule mismatch", reason)

    def test_assembly_vs_spare_veto(self):
        specs_kit = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": True}
        specs_spare = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": False}
        
        is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_kit, specs_spare)
        self.assertTrue(is_vetoed)
        self.assertIn("Assembly Token Veto", reason)

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

if __name__ == "__main__":
    unittest.main()
