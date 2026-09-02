from typing import Dict, Any, Tuple, Optional
from app.services.normalization.spec_extractor import INCH_MM_MAP

class SafetyGuardrails:
    """
    Hard Deterministic Safety Invariant Veto Engine.
    Guarantees that safety-critical mismatch errors (e.g. pressure rating, wall thickness,
    kit vs spare) are vetoed before merging, preventing refinery hazards.
    """

    @staticmethod
    def _canonicalize_size(size_str: Optional[str]) -> Optional[str]:
        if not size_str:
            return None
        clean = size_str.strip().upper()
        # Direct lookup
        if clean in INCH_MM_MAP:
            return INCH_MM_MAP[clean]
        # Compacted lookup (e.g. "6 MM" -> "6MM")
        compact = clean.replace(" ", "")
        if compact in INCH_MM_MAP:
            return INCH_MM_MAP[compact]
        return clean

    @staticmethod
    def evaluate_pair(specs_a: Dict[str, Any], specs_b: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluates two parsed specifications for hard safety conflicts.
        Returns: (is_vetoed: bool, veto_reason: Optional[str], suggested_route: Optional[str])
        """
        # 1. Item Noun Invariant
        noun_a = specs_a.get("item_noun")
        noun_b = specs_b.get("item_noun")
        if noun_a and noun_b and noun_a != noun_b:
            return True, f"Fundamental item type mismatch: '{noun_a}' vs '{noun_b}'", "REJECT"

        # 2. Safety-Critical Pressure Class Mismatch
        press_a = specs_a.get("pressure_class")
        press_b = specs_b.get("pressure_class")
        if press_a and press_b and press_a != press_b:
            return True, f"Refinery Safety Veto: Pressure rating conflict ({press_a} vs {press_b})", "SUBSTITUTE"

        # 3. Nominal Size Conflict (Resolved with Canonical Equivalence)
        size_a = specs_a.get("nominal_size")
        size_b = specs_b.get("nominal_size")
        if size_a and size_b:
            canon_a = SafetyGuardrails._canonicalize_size(size_a)
            canon_b = SafetyGuardrails._canonicalize_size(size_b)
            if canon_a and canon_b and canon_a != canon_b:
                return True, f"Physical dimension mismatch: Nominal size ({size_a} vs {size_b})", "REJECT"

        # 4. Schedule / Wall Thickness Conflict
        sch_a = specs_a.get("schedule")
        sch_b = specs_b.get("schedule")
        if sch_a and sch_b and sch_a != sch_b:
            return True, f"Refinery Safety Veto: Wall thickness schedule mismatch ({sch_a} vs {sch_b})", "SUBSTITUTE"

        # 5. Assembly / Kit vs Spare Component Veto
        kit_a = specs_a.get("is_kit_or_assembly", False)
        kit_b = specs_b.get("is_kit_or_assembly", False)
        if kit_a != kit_b:
            return True, "Assembly Token Veto: Complete assembly/kit cannot merge with component spare", "REJECT"

        # 6. Material Metallurgy (MOC) Incompatibility
        moc_a = specs_a.get("moc")
        moc_b = specs_b.get("moc")
        if moc_a and moc_b:
            # Check Carbon Steel vs Stainless Steel mismatch
            is_cs_a = "CARBON" in moc_a or "CS" in moc_a or "WCB" in moc_a or "A105" in moc_a or "A106" in moc_a
            is_cs_b = "CARBON" in moc_b or "CS" in moc_b or "WCB" in moc_b or "A105" in moc_b or "A106" in moc_b
            is_ss_a = "STAINLESS" in moc_a or "SS" in moc_a or "CF8" in moc_a or "316" in moc_a or "304" in moc_a
            is_ss_b = "STAINLESS" in moc_b or "SS" in moc_b or "CF8" in moc_b or "316" in moc_b or "304" in moc_b
            
            if (is_cs_a and is_ss_b) or (is_ss_a and is_cs_b):
                return True, f"Metallurgy Incompatibility: Carbon Steel vs Stainless Steel ({moc_a} vs {moc_b})", "SUBSTITUTE"

        # 7. Bearing & OEM Part Number Handling
        clean_part_a = specs_a.get("clean_part_number")
        clean_part_b = specs_b.get("clean_part_number")
        clearance_a = specs_a.get("clearance_suffix")
        clearance_b = specs_b.get("clearance_suffix")
        
        if clean_part_a and clean_part_b:
            if clean_part_a != clean_part_b:
                return True, f"OEM Part Number mismatch: '{clean_part_a}' vs '{clean_part_b}'", "REJECT"
            elif clearance_a != clearance_b:
                return True, f"Bearing Clearance Modifier Difference: '{clearance_a or 'STD'}' vs '{clearance_b or 'STD'}'", "SUBSTITUTE"

        # 8. Electrical Voltage & Current Rating Invariants
        volt_a = specs_a.get("voltage_rating")
        volt_b = specs_b.get("voltage_rating")
        if volt_a and volt_b and volt_a != volt_b:
            return True, f"Electrical Safety Veto: Voltage rating conflict ({volt_a} vs {volt_b})", "REJECT"

        curr_a = specs_a.get("current_rating")
        curr_b = specs_b.get("current_rating")
        if curr_a and curr_b and curr_a != curr_b:
            return True, f"Electrical Safety Veto: Current rating conflict ({curr_a} vs {curr_b})", "SUBSTITUTE"

        # 9. Fastener Thread Standard & Size Invariant
        thread_a = specs_a.get("thread_size")
        thread_b = specs_b.get("thread_size")
        if thread_a and thread_b and thread_a != thread_b:
            return True, f"Mechanical Fit Veto: Fastener thread size mismatch ({thread_a} vs {thread_b})", "REJECT"

        # 10. Steel Sector Invariants (Rebar Grade & Refractory Temp/Alumina)
        grade_a = specs_a.get("steel_grade")
        grade_b = specs_b.get("steel_grade")
        if grade_a and grade_b and grade_a != grade_b:
            return True, f"Structural Safety Veto: Steel rebar yield strength grade mismatch ({grade_a} vs {grade_b})", "SUBSTITUTE"

        alumina_a = specs_a.get("alumina_content")
        alumina_b = specs_b.get("alumina_content")
        if alumina_a and alumina_b and alumina_a != alumina_b:
            return True, f"Refractory Thermal Veto: Alumina percentage specification mismatch ({alumina_a} vs {alumina_b})", "SUBSTITUTE"

        # 11. Mining Sector Invariants (Conveyor Belt Width & Tensile Rating)
        b_width_a = specs_a.get("belt_width")
        b_width_b = specs_b.get("belt_width")
        if b_width_a and b_width_b and b_width_a != b_width_b:
            return True, f"Mining Safety Veto: Conveyor belt width physical mismatch ({b_width_a} vs {b_width_b})", "REJECT"

        adapter_a = specs_a.get("adapter_fitment_system")
        adapter_b = specs_b.get("adapter_fitment_system")
        if adapter_a and adapter_b and adapter_a != adapter_b:
            return True, f"Mining Safety Veto: Bucket tooth adapter fitment system mismatch ({adapter_a} vs {adapter_b})", "REJECT"

        return False, None, None
