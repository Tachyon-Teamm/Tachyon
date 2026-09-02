import re
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
        # Direct lookup in keys
        if clean in INCH_MM_MAP:
            return INCH_MM_MAP[clean]
        # Compacted lookup (e.g. "6 MM" -> "6MM")
        compact = clean.replace(" ", "")
        if compact in INCH_MM_MAP:
            return INCH_MM_MAP[compact]
        # Check if clean is already one of the canonical values
        for k, v in INCH_MM_MAP.items():
            if clean == v.upper() or compact == v.replace(" ", "").upper():
                return v
        return clean

    @staticmethod
    def _canonicalize_pressure(press_str: Optional[str]) -> Optional[str]:
        if not press_str:
            return None
        clean = press_str.strip().upper()
        m = re.search(r'(?:CL(?:ASS)?\s*(\d{2,4})|PN\s*(\d{2,4})|(\d{2,4})\s*#|(\d{2,4})\s*LBS?)', clean)
        if m:
            val = m.group(1) or m.group(2) or m.group(3) or m.group(4)
            if "PN" in clean:
                return f"PN {val}"
            return f"CLASS {val}#"
        return clean.replace(" ", "")

    @staticmethod
    def evaluate_pair(specs_a: Dict[str, Any], specs_b: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluates two parsed specifications for hard safety conflicts.
        Returns: (is_vetoed: bool, veto_reason: Optional[str], suggested_route: Optional[str])
        """
        # 1. Item Noun Invariant
        noun_a = specs_a.get("item_noun")
        noun_b = specs_b.get("item_noun")
        if noun_a and noun_b and str(noun_a).strip().upper() != str(noun_b).strip().upper():
            return True, f"Fundamental item type mismatch: '{noun_a}' vs '{noun_b}'", "REJECT"

        # 2. Safety-Critical Pressure Class Mismatch
        press_a = specs_a.get("pressure_class")
        press_b = specs_b.get("pressure_class")
        if press_a and press_b:
            c_press_a = SafetyGuardrails._canonicalize_pressure(str(press_a))
            c_press_b = SafetyGuardrails._canonicalize_pressure(str(press_b))
            if c_press_a and c_press_b and c_press_a != c_press_b:
                return True, f"Refinery Safety Veto: Pressure rating conflict ({press_a} vs {press_b})", "SUBSTITUTE"

        # 3. Nominal Size Conflict (Resolved with Canonical Equivalence)
        size_a = specs_a.get("nominal_size")
        size_b = specs_b.get("nominal_size")
        if size_a and size_b:
            canon_a = SafetyGuardrails._canonicalize_size(str(size_a))
            canon_b = SafetyGuardrails._canonicalize_size(str(size_b))
            if canon_a and canon_b and canon_a != canon_b:
                return True, f"Physical dimension mismatch: Nominal size ({size_a} vs {size_b})", "REJECT"

        # 4. Schedule / Wall Thickness Conflict
        sch_a = specs_a.get("schedule")
        sch_b = specs_b.get("schedule")
        if sch_a and sch_b:
            c_sch_a = re.sub(r'[^0-9A-Z]', '', str(sch_a).upper())
            c_sch_b = re.sub(r'[^0-9A-Z]', '', str(sch_b).upper())
            if c_sch_a != c_sch_b:
                return True, f"Refinery Safety Veto: Wall thickness schedule mismatch ({sch_a} vs {sch_b})", "SUBSTITUTE"

        # 5. Assembly / Kit vs Spare Component Veto
        kit_a = specs_a.get("is_kit_or_assembly", False)
        kit_b = specs_b.get("is_kit_or_assembly", False)
        if kit_a != kit_b:
            return True, "Assembly Token Veto: Complete assembly/kit cannot merge with component spare", "REJECT"

        # 6. Material Metallurgy (MOC) Incompatibility
        moc_a = str(specs_a.get("moc") or "").upper()
        moc_b = str(specs_b.get("moc") or "").upper()
        if moc_a and moc_b:
            is_cs_a = any(k in moc_a for k in ["CARBON", "CS", "WCB", "A105", "A106"])
            is_cs_b = any(k in moc_b for k in ["CARBON", "CS", "WCB", "A105", "A106"])
            is_ss_a = any(k in moc_a for k in ["STAINLESS", "SS", "CF8", "316", "304"])
            is_ss_b = any(k in moc_b for k in ["STAINLESS", "SS", "CF8", "316", "304"])
            
            if (is_cs_a and is_ss_b) or (is_ss_a and is_cs_b):
                return True, f"Metallurgy Incompatibility: Carbon Steel vs Stainless Steel ({specs_a.get('moc')} vs {specs_b.get('moc')})", "SUBSTITUTE"

        # 7. Bearing & OEM Part Number Handling
        clean_part_a = str(specs_a.get("clean_part_number") or "").strip().upper()
        clean_part_b = str(specs_b.get("clean_part_number") or "").strip().upper()
        clearance_a = (specs_a.get("clearance_suffix") or "STD").strip().upper()
        clearance_b = (specs_b.get("clearance_suffix") or "STD").strip().upper()
        
        if clean_part_a and clean_part_b:
            if clean_part_a != clean_part_b:
                return True, f"OEM Part Number mismatch: '{clean_part_a}' vs '{clean_part_b}'", "REJECT"
            elif clearance_a != clearance_b:
                return True, f"Bearing Clearance Modifier Difference: '{clearance_a}' vs '{clearance_b}'", "SUBSTITUTE"

        # 8. Electrical Voltage & Current Rating Invariants
        volt_a = specs_a.get("voltage_rating")
        volt_b = specs_b.get("voltage_rating")
        if volt_a and volt_b:
            c_volt_a = re.sub(r'[^0-9A-Z]', '', str(volt_a).upper())
            c_volt_b = re.sub(r'[^0-9A-Z]', '', str(volt_b).upper())
            if c_volt_a != c_volt_b:
                return True, f"Electrical Safety Veto: Voltage rating conflict ({volt_a} vs {volt_b})", "REJECT"

        curr_a = specs_a.get("current_rating")
        curr_b = specs_b.get("current_rating")
        if curr_a and curr_b:
            c_curr_a = re.sub(r'[^0-9A-Z]', '', str(curr_a).upper())
            c_curr_b = re.sub(r'[^0-9A-Z]', '', str(curr_b).upper())
            if c_curr_a != c_curr_b:
                return True, f"Electrical Safety Veto: Current rating conflict ({curr_a} vs {curr_b})", "SUBSTITUTE"

        # 9. Fastener Thread Standard & Size Invariant
        thread_a = specs_a.get("thread_size")
        thread_b = specs_b.get("thread_size")
        if thread_a and thread_b:
            c_thread_a = re.sub(r'[^0-9A-Z]', '', str(thread_a).upper())
            c_thread_b = re.sub(r'[^0-9A-Z]', '', str(thread_b).upper())
            if c_thread_a != c_thread_b:
                return True, f"Mechanical Fit Veto: Fastener thread size mismatch ({thread_a} vs {thread_b})", "REJECT"

        # 10. Steel Sector Invariants (Rebar Grade & Refractory Temp/Alumina)
        grade_a = specs_a.get("steel_grade")
        grade_b = specs_b.get("steel_grade")
        if grade_a and grade_b and str(grade_a).strip().upper() != str(grade_b).strip().upper():
            return True, f"Structural Safety Veto: Steel rebar yield strength grade mismatch ({grade_a} vs {grade_b})", "SUBSTITUTE"

        alumina_a = specs_a.get("alumina_content")
        alumina_b = specs_b.get("alumina_content")
        if alumina_a and alumina_b and str(alumina_a).strip().upper() != str(alumina_b).strip().upper():
            return True, f"Refractory Thermal Veto: Alumina percentage specification mismatch ({alumina_a} vs {alumina_b})", "SUBSTITUTE"

        # 11. Mining Sector Invariants (Conveyor Belt Width & Tensile Rating)
        b_width_a = specs_a.get("belt_width")
        b_width_b = specs_b.get("belt_width")
        if b_width_a and b_width_b and str(b_width_a).strip().upper() != str(b_width_b).strip().upper():
            return True, f"Mining Safety Veto: Conveyor belt width physical mismatch ({b_width_a} vs {b_width_b})", "REJECT"

        adapter_a = specs_a.get("adapter_fitment_system")
        adapter_b = specs_b.get("adapter_fitment_system")
        if adapter_a and adapter_b and str(adapter_a).strip().upper() != str(adapter_b).strip().upper():
            return True, f"Mining Safety Veto: Bucket tooth adapter fitment system mismatch ({adapter_a} vs {adapter_b})", "REJECT"

        return False, None, "IDENTICAL"
