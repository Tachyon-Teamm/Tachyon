import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.normalization.spec_extractor import SpecExtractor

class TestSpecExtractor(unittest.TestCase):
    def test_valve_spec_extraction(self):
        desc1 = "VLV GATE 6IN 300# CS FLG"
        specs1 = SpecExtractor.extract_specs(desc1)
        self.assertEqual(specs1["item_noun"], "VALVE, GATE")
        self.assertEqual(specs1["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs1["pressure_class"], "CLASS 300#")
        self.assertTrue(specs1["moc"] == "ASTM A216 WCB" or "CARBON" in (specs1["moc"] or ""))
        self.assertEqual(specs1["end_connection"], "FLANGED RF")

        desc2 = "VALVE, GATE, 150MM, CL300, WCB"
        specs2 = SpecExtractor.extract_specs(desc2)
        self.assertEqual(specs2["item_noun"], "VALVE, GATE")
        self.assertEqual(specs2["nominal_size"], "6 INCH (150 MM)")
        self.assertEqual(specs2["pressure_class"], "CLASS 300#")
        self.assertEqual(specs2["moc"], "ASTM A216 WCB")

    def test_pipe_schedule_extraction(self):
        desc_sch40 = "PIPE CS SMLS 4\" SCH 40 ASTM A106"
        specs_sch40 = SpecExtractor.extract_specs(desc_sch40)
        self.assertEqual(specs_sch40["item_noun"], "PIPE")
        self.assertEqual(specs_sch40["nominal_size"], "4 INCH (100 MM)")
        self.assertEqual(specs_sch40["schedule"], "SCH 40")
        self.assertEqual(specs_sch40["moc"], "ASTM A106 GR.B")

        desc_sch80 = "PIPE CS 4\" SCH 80 A106"
        specs_sch80 = SpecExtractor.extract_specs(desc_sch80)
        self.assertEqual(specs_sch80["schedule"], "SCH 80")

    def test_bearing_part_number_and_clearance(self):
        desc1 = "BEARING 6205-2RS1 SKF"
        specs1 = SpecExtractor.extract_specs(desc1)
        self.assertEqual(specs1["item_noun"], "BEARING")
        self.assertEqual(specs1["clean_part_number"], "62052RS1")
        self.assertEqual(specs1["brand"], "SKF")

        desc2 = "SKF BEARING NO. 6205 2RS1 / C3"
        specs2 = SpecExtractor.extract_specs(desc2)
        self.assertEqual(specs2["clearance_suffix"], "C3")

    def test_assembly_vs_spare_detection(self):
        assembly_desc = "MECH SEAL CARTRIDGE PUMP P-101A (SET)"
        spare_desc = "ROTARY SEAL RING FOR PUMP P-101A"
        
        self.assertTrue(SpecExtractor.extract_specs(assembly_desc)["is_kit_or_assembly"])
        self.assertFalse(SpecExtractor.extract_specs(spare_desc)["is_kit_or_assembly"])

    def test_part_number_pn_vs_pressure_class(self):
        desc = "VALVE GATE 6IN 300# PN: 889102"
        specs = SpecExtractor.extract_specs(desc)
        self.assertEqual(specs["pressure_class"], "CLASS 300#")
        self.assertNotEqual(specs["pressure_class"], "PN 300")

    def test_compound_gasket_noun_priority(self):
        desc = "GASKET FOR GATE VALVE 6IN 300#"
        specs = SpecExtractor.extract_specs(desc)
        self.assertEqual(specs["item_noun"], "GASKET")

    def test_multi_sector_attributes(self):
        cbl_desc = "CABLE XLPE 3CX240 SQMM 11KV 630A 3P"
        cbl_specs = SpecExtractor.extract_specs(cbl_desc)
        self.assertEqual(cbl_specs["item_noun"], "CABLE")
        self.assertEqual(cbl_specs["voltage_rating"], "11KV")
        self.assertEqual(cbl_specs["current_rating"], "630A")
        self.assertEqual(cbl_specs["pole_count"], "3P")

        bolt_desc = "HEX BOLT M16 X 65 MM GRADE 8.8"
        bolt_specs = SpecExtractor.extract_specs(bolt_desc)
        self.assertEqual(bolt_specs["item_noun"], "FASTENER")
        self.assertEqual(bolt_specs["thread_size"], "M16")
        self.assertEqual(bolt_specs["length"], "65 MM")

if __name__ == "__main__":
    unittest.main()
