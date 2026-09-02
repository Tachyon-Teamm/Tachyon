import pytest
from app.services.matching.guardrails import SafetyGuardrails

def test_pressure_mismatch_veto():
    specs_150 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 150#"}
    specs_300 = {"item_noun": "VALVE, GATE", "nominal_size": "2 INCH (50 MM)", "pressure_class": "CLASS 300#"}
    
    is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_150, specs_300)
    assert is_vetoed is True
    assert "Pressure rating conflict" in reason
    assert route == "SUBSTITUTE"

def test_schedule_mismatch_veto():
    specs_sch40 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 40"}
    specs_sch80 = {"item_noun": "PIPE", "nominal_size": "4 INCH (100 MM)", "schedule": "SCH 80"}
    
    is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_sch40, specs_sch80)
    assert is_vetoed is True
    assert "Wall thickness schedule mismatch" in reason

def test_assembly_vs_spare_veto():
    specs_kit = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": True}
    specs_spare = {"item_noun": "MECHANICAL SEAL", "is_kit_or_assembly": False}
    
    is_vetoed, reason, route = SafetyGuardrails.evaluate_pair(specs_kit, specs_spare)
    assert is_vetoed is True
    assert "Assembly Token Veto" in reason

def test_compatible_pair_passes():
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
    assert is_vetoed is False
    assert reason is None
