import pytest
from app.services.normalization.spec_extractor import SpecExtractor

def test_valve_spec_extraction():
    desc1 = "VLV GATE 6IN 300# CS FLG"
    specs1 = SpecExtractor.extract_specs(desc1)
    assert specs1["item_noun"] == "VALVE, GATE"
    assert specs1["nominal_size"] == "6 INCH (150 MM)"
    assert specs1["pressure_class"] == "CLASS 300#"
    assert specs1["moc"] == "ASTM A216 WCB" or "CARBON" in specs1["moc"]
    assert specs1["end_connection"] == "FLANGED RF"

    desc2 = "VALVE, GATE, 150MM, CL300, WCB"
    specs2 = SpecExtractor.extract_specs(desc2)
    assert specs2["item_noun"] == "VALVE, GATE"
    assert specs2["nominal_size"] == "6 INCH (150 MM)"
    assert specs2["pressure_class"] == "CLASS 300#"
    assert specs2["moc"] == "ASTM A216 WCB"

def test_pipe_schedule_extraction():
    desc_sch40 = "PIPE CS SMLS 4\" SCH 40 ASTM A106"
    specs_sch40 = SpecExtractor.extract_specs(desc_sch40)
    assert specs_sch40["item_noun"] == "PIPE"
    assert specs_sch40["nominal_size"] == "4 INCH (100 MM)"
    assert specs_sch40["schedule"] == "SCH 40"
    assert specs_sch40["moc"] == "ASTM A106 GR.B"

    desc_sch80 = "PIPE CS 4\" SCH 80 A106"
    specs_sch80 = SpecExtractor.extract_specs(desc_sch80)
    assert specs_sch80["schedule"] == "SCH 80"

def test_bearing_part_number_and_clearance():
    desc1 = "BEARING 6205-2RS1 SKF"
    specs1 = SpecExtractor.extract_specs(desc1)
    assert specs1["item_noun"] == "BEARING"
    assert specs1["clean_part_number"] == "62052RS1"
    assert specs1["brand"] == "SKF"

    desc2 = "SKF BEARING NO. 6205 2RS1 / C3"
    specs2 = SpecExtractor.extract_specs(desc2)
    assert specs2["clearance_suffix"] == "C3"

def test_assembly_vs_spare_detection():
    assembly_desc = "MECH SEAL CARTRIDGE PUMP P-101A (SET)"
    spare_desc = "ROTARY SEAL RING FOR PUMP P-101A"
    
    assert SpecExtractor.extract_specs(assembly_desc)["is_kit_or_assembly"] is True
    assert SpecExtractor.extract_specs(spare_desc)["is_kit_or_assembly"] is False
