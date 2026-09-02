import re
from typing import Dict, Any, Optional, Tuple
from app.services.normalization.domain_lexicon import DomainLexicon

# Standard Nominal Dimension Mapping (Inches <-> Millimeters)
INCH_MM_MAP: Dict[str, str] = {
    '1/4"': "1/4 INCH (6 MM)", '1/4 INCH': "1/4 INCH (6 MM)", '1/4IN': "1/4 INCH (6 MM)", '6MM': "1/4 INCH (6 MM)", '6 MM': "1/4 INCH (6 MM)", 'DN6': "1/4 INCH (6 MM)",
    '3/8"': "3/8 INCH (10 MM)", '3/8 INCH': "3/8 INCH (10 MM)", '3/8IN': "3/8 INCH (10 MM)", '10MM': "3/8 INCH (10 MM)", '10 MM': "3/8 INCH (10 MM)", 'DN10': "3/8 INCH (10 MM)",
    '1/2"': "1/2 INCH (15 MM)", '1/2 INCH': "1/2 INCH (15 MM)", '1/2IN': "1/2 INCH (15 MM)", '0.5"': "1/2 INCH (15 MM)", '15MM': "1/2 INCH (15 MM)", '15 MM': "1/2 INCH (15 MM)", 'DN15': "1/2 INCH (15 MM)",
    '3/4"': "3/4 INCH (20 MM)", '3/4 INCH': "3/4 INCH (20 MM)", '3/4IN': "3/4 INCH (20 MM)", '0.75"': "3/4 INCH (20 MM)", '20MM': "3/4 INCH (20 MM)", '20 MM': "3/4 INCH (20 MM)", 'DN20': "3/4 INCH (20 MM)",
    '1"': "1 INCH (25 MM)", '1 INCH': "1 INCH (25 MM)", '1IN': "1 INCH (25 MM)", '25MM': "1 INCH (25 MM)", '25 MM': "1 INCH (25 MM)", 'DN25': "1 INCH (25 MM)",
    '1.25"': "1-1/4 INCH (32 MM)", '1 1/4"': "1-1/4 INCH (32 MM)", '1-1/4"': "1-1/4 INCH (32 MM)", '1-1/4 INCH': "1-1/4 INCH (32 MM)", '32MM': "1-1/4 INCH (32 MM)", '32 MM': "1-1/4 INCH (32 MM)", 'DN32': "1-1/4 INCH (32 MM)",
    '1.5"': "1-1/2 INCH (40 MM)", '1 1/2"': "1-1/2 INCH (40 MM)", '1-1/2"': "1-1/2 INCH (40 MM)", '1-1/2 INCH': "1-1/2 INCH (40 MM)", '40MM': "1-1/2 INCH (40 MM)", '40 MM': "1-1/2 INCH (40 MM)", 'DN40': "1-1/2 INCH (40 MM)",
    '2"': "2 INCH (50 MM)", '2 INCH': "2 INCH (50 MM)", '2IN': "2 INCH (50 MM)", '50MM': "2 INCH (50 MM)", '50 MM': "2 INCH (50 MM)", 'DN50': "2 INCH (50 MM)",
    '2.5"': "2-1/2 INCH (65 MM)", '2 1/2"': "2-1/2 INCH (65 MM)", '2-1/2"': "2-1/2 INCH (65 MM)", '2-1/2 INCH': "2-1/2 INCH (65 MM)", '65MM': "2-1/2 INCH (65 MM)", '65 MM': "2-1/2 INCH (65 MM)", 'DN65': "2-1/2 INCH (65 MM)",
    '3"': "3 INCH (80 MM)", '3 INCH': "3 INCH (80 MM)", '3IN': "3 INCH (80 MM)", '80MM': "3 INCH (80 MM)", '80 MM': "3 INCH (80 MM)", 'DN80': "3 INCH (80 MM)",
    '4"': "4 INCH (100 MM)", '4 INCH': "4 INCH (100 MM)", '4IN': "4 INCH (100 MM)", '100MM': "4 INCH (100 MM)", '100 MM': "4 INCH (100 MM)", 'DN100': "4 INCH (100 MM)",
    '6"': "6 INCH (150 MM)", '6 INCH': "6 INCH (150 MM)", '6IN': "6 INCH (150 MM)", '150MM': "6 INCH (150 MM)", '150 MM': "6 INCH (150 MM)", 'DN150': "6 INCH (150 MM)",
    '8"': "8 INCH (200 MM)", '8 INCH': "8 INCH (200 MM)", '8IN': "8 INCH (200 MM)", '200MM': "8 INCH (200 MM)", '200 MM': "8 INCH (200 MM)", 'DN200': "8 INCH (200 MM)",
    '10"': "10 INCH (250 MM)", '10 INCH': "10 INCH (250 MM)", '10IN': "10 INCH (250 MM)", '250MM': "10 INCH (250 MM)", '250 MM': "10 INCH (250 MM)", 'DN250': "10 INCH (250 MM)",
    '12"': "12 INCH (300 MM)", '12 INCH': "12 INCH (300 MM)", '12IN': "12 INCH (300 MM)", '300MM': "12 INCH (300 MM)", '300 MM': "12 INCH (300 MM)", 'DN300': "12 INCH (300 MM)",
    '14"': "14 INCH (350 MM)", '14 INCH': "14 INCH (350 MM)", '14IN': "14 INCH (350 MM)", '350MM': "14 INCH (350 MM)", '350 MM': "14 INCH (350 MM)", 'DN350': "14 INCH (350 MM)",
    '16"': "16 INCH (400 MM)", '16 INCH': "16 INCH (400 MM)", '16IN': "16 INCH (400 MM)", '400MM': "16 INCH (400 MM)", '400 MM': "16 INCH (400 MM)", 'DN400': "16 INCH (400 MM)",
    '18"': "18 INCH (450 MM)", '18 INCH': "18 INCH (450 MM)", '18IN': "18 INCH (450 MM)", '450MM': "18 INCH (450 MM)", '450 MM': "18 INCH (450 MM)", 'DN450': "18 INCH (450 MM)",
    '20"': "20 INCH (500 MM)", '20 INCH': "20 INCH (500 MM)", '20IN': "20 INCH (500 MM)", '500MM': "20 INCH (500 MM)", '500 MM': "20 INCH (500 MM)", 'DN500': "20 INCH (500 MM)",
    '24"': "24 INCH (600 MM)", '24 INCH': "24 INCH (600 MM)", '24IN': "24 INCH (600 MM)", '600MM': "24 INCH (600 MM)", '600 MM': "24 INCH (600 MM)", 'DN600': "24 INCH (600 MM)"
}

class SpecExtractor:
    @staticmethod
    def extract_specs(raw_description: str) -> Dict[str, Any]:
        """
        Deterministic regex-based parametric spec extractor.
        Zero ML training required.
        """
        desc = DomainLexicon.preprocess_text(raw_description)
        specs: Dict[str, Any] = {
            "item_noun": None,
            "nominal_size": None,
            "pressure_class": None,
            "moc": None,
            "schedule": None,
            "end_connection": None,
            "standard_spec": None,
            "part_number": None,
            "clean_part_number": None,
            "clearance_suffix": None,
            "brand": None,
            "is_kit_or_assembly": False,
            "raw_preprocessed": desc
        }
        
        # 1. Item Noun Extraction
        if re.search(r'\bVALVE\b|\bVLV\b', desc):
            if re.search(r'\bGATE\b', desc):
                specs["item_noun"] = "VALVE, GATE"
            elif re.search(r'\bGLOBE\b', desc):
                specs["item_noun"] = "VALVE, GLOBE"
            elif re.search(r'\bBALL\b', desc):
                specs["item_noun"] = "VALVE, BALL"
            elif re.search(r'\bCHECK\b|\bNRV\b', desc):
                specs["item_noun"] = "VALVE, CHECK"
            elif re.search(r'\bBUTTERFLY\b', desc):
                specs["item_noun"] = "VALVE, BUTTERFLY"
            elif re.search(r'\bPLUG\b', desc):
                specs["item_noun"] = "VALVE, PLUG"
            elif re.search(r'\bSAFETY\b|\bRELIEF\b|\bPSV\b', desc):
                specs["item_noun"] = "VALVE, SAFETY RELIEF"
            else:
                specs["item_noun"] = "VALVE"
        elif re.search(r'\bPIPE\b|\bTUBING\b', desc):
            specs["item_noun"] = "PIPE"
        elif re.search(r'\bFLANGE\b|\bFLG\b', desc) and not re.search(r'\bVALVE\b', desc):
            specs["item_noun"] = "FLANGE"
        elif re.search(r'\bGASKET\b', desc):
            if "SPIRAL" in desc:
                specs["item_noun"] = "GASKET, SPIRAL WOUND"
            else:
                specs["item_noun"] = "GASKET"
        elif re.search(r'\bBEARING\b|\bBRG\b', desc):
            specs["item_noun"] = "BEARING"
        elif re.search(r'\bMECHANICAL\s*SEAL\b|\bMECH\s*SEAL\b|\bOIL\s*SEAL\b|\bSEAL\b', desc):
            specs["item_noun"] = "MECHANICAL SEAL"
        elif re.search(r'\bGREASE\b|\bLUBRICANT\b|\bOIL\b', desc):
            specs["item_noun"] = "LUBRICANT / GREASE"

        # 2. Nominal Size Extraction
        # Check compound fraction first: e.g. 1-1/2", 1 1/2", 2-1/2", 1-1/4"
        compound_pat = re.search(
            r'(?:^|\s|\b)(\d+)\s*[- ]\s*(\d+/\d+)\s*(?:\"|\'|INCH|IN)?(?:\s|$|[^\w\d])',
            desc
        )
        if compound_pat:
            whole, frac = compound_pat.group(1), compound_pat.group(2)
            c_key = f'{whole}-{frac}"'
            if c_key in INCH_MM_MAP:
                specs["nominal_size"] = INCH_MM_MAP[c_key]
            else:
                specs["nominal_size"] = f'{whole}-{frac} INCH'
        else:
            size_pat = re.search(
                r'(?:^|\s|\b)(\d+(?:\.\d+)?\s*(?:\"|\'|INCH|IN|MM)|DN\s*\d+|\d+/\d+\s*(?:\"|\'|INCH|IN)?)(?:\s|$|[^\w\d])',
                desc
            )
            if size_pat:
                matched_size = size_pat.group(1).replace(" ", "").upper()
                if matched_size in INCH_MM_MAP:
                    specs["nominal_size"] = INCH_MM_MAP[matched_size]
                else:
                    num_only = re.match(r'(\d+)(?:INCH|IN|\")', matched_size)
                    if num_only:
                        val = num_only.group(1)
                        inch_key = f'{val}"'
                        specs["nominal_size"] = INCH_MM_MAP.get(inch_key, f'{val} INCH')
                    else:
                        specs["nominal_size"] = matched_size

        # 3. Pressure Rating Extraction
        direct_press = re.search(r'\b(?:CL(?:ASS)?\s*(\d{2,4})|PN\s*(\d{2,4})|(\d{2,4})\s*#|(\d{2,4})\s*LBS?)\b', desc)
        if direct_press:
            val = direct_press.group(1) or direct_press.group(2) or direct_press.group(3) or direct_press.group(4)
            if "PN" in desc:
                specs["pressure_class"] = f"PN {val}"
            else:
                specs["pressure_class"] = f"CLASS {val}#"
        elif re.search(r'\b(\d{2,4})#', desc):
            val = re.search(r'\b(\d{2,4})#', desc).group(1)
            specs["pressure_class"] = f"CLASS {val}#"

        # 4. Material of Construction (MOC) / Metallurgy
        if re.search(r'\bASTM\s*A216\s*WCB\b|\bWCB\b', desc):
            specs["moc"] = "ASTM A216 WCB"
        elif re.search(r'\bASTM\s*A106\s*(?:GR\.?\s*B)?\b|\bA106\b', desc):
            specs["moc"] = "ASTM A106 GR.B"
        elif re.search(r'\bASTM\s*A105\b|\bA105\b', desc):
            specs["moc"] = "ASTM A105"
        elif re.search(r'\bSS\s*316L?\b|\bSTAINLESS\s*STEEL\s*316\b|\bCF8M\b|\bTP316\b', desc):
            specs["moc"] = "STAINLESS STEEL 316 (CF8M/TP316)"
        elif re.search(r'\bSS\s*304L?\b|\bSTAINLESS\s*STEEL\s*304\b|\bCF8\b|\bTP304\b', desc):
            specs["moc"] = "STAINLESS STEEL 304 (CF8/TP304)"
        elif re.search(r'\bCARBON\s*STEEL\b|\bCS\b', desc):
            specs["moc"] = "ASTM A216 WCB"
        elif re.search(r'\bMONEL\b', desc):
            specs["moc"] = "MONEL"
        elif re.search(r'\bINCONEL\b', desc):
            specs["moc"] = "INCONEL"
        elif re.search(r'\bDUPLEX\b', desc):
            specs["moc"] = "DUPLEX STAINLESS STEEL"

        # 5. Schedule (Wall Thickness)
        sch_pat = re.search(r'\bSCH(?:EDULE)?\s*(\d+|STD|XS|XXS)\b', desc)
        if sch_pat:
            specs["schedule"] = f"SCH {sch_pat.group(1).upper()}"

        # 6. End Connection
        if re.search(r'\bFLANGED?\s*RF\b|\bFLG\s*RF\b|\bRAISED\s*FACE\b|\bFLG\b|\bFLANGED?\b|\bFLANGE\b', desc):
            specs["end_connection"] = "FLANGED RF"
        elif re.search(r'\bFLANGED?\s*RTJ\b|\bRTJ\b', desc):
            specs["end_connection"] = "FLANGED RTJ"
        elif re.search(r'\bBUTT\s*WELD\b|\bBW\b', desc):
            specs["end_connection"] = "BUTT WELD"
        elif re.search(r'\bSOCKET\s*WELD\b|\bSW\b', desc):
            specs["end_connection"] = "SOCKET WELD"
        elif re.search(r'\bTHREADED\b|\bNPT\b', desc):
            specs["end_connection"] = "THREADED NPT"

        # 7. Standard Spec
        std_pat = re.search(r'\b(ASME\s*B16\.\d+|ANSI\s*B16\.\d+|API\s*6D|API\s*600|API\s*602|BS\s*\d+|ISO\s*\d+)\b', desc)
        if std_pat:
            specs["standard_spec"] = DomainLexicon.normalize_standard(std_pat.group(1))

        # 8. Bearing & OEM Part Number Canonicalizer
        for brand in ["SKF", "FAG", "TIMKEN", "NSK", "NTN", "SCHAEFFLER"]:
            if brand in desc:
                specs["brand"] = brand
                break
                
        part_match = re.search(r'\b([0-9]{4,5}(?:[-/ ][A-Z0-9]+)*)\b', desc)
        if part_match and (specs["item_noun"] == "BEARING" or specs["brand"]):
            raw_part = part_match.group(1)
            for b in ["SKF", "FAG", "TIMKEN", "NSK", "NTN"]:
                if raw_part.endswith(f" {b}") or raw_part.endswith(f"-{b}"):
                    raw_part = raw_part[:-len(b)-1].strip()
            specs["part_number"] = raw_part
            
            suffixes = re.findall(r'(?:[/ -]|\b)(C2|C3|C4|C5|2RS1|2RS|ZZ|2Z|RS|BECBP)\b', desc)
            if suffixes:
                c_matches = [s for s in suffixes if s in ["C2", "C3", "C4", "C5"]]
                if c_matches:
                    specs["clearance_suffix"] = c_matches[-1]
                else:
                    specs["clearance_suffix"] = suffixes[-1]
                
            clean_p = re.sub(r'[^A-Z0-9]', '', raw_part)
            specs["clean_part_number"] = clean_p

        # 9. Assembly / Kit vs Component Spare Detection
        assembly_keywords = [r'\bSET\b', r'\bKIT\b', r'\bASSY\b', r'\bASSEMBLY\b', r'\bCOMPLETE\s*SET\b', r'\bCARTRIDGE\b']
        spare_keywords = [r'\bSPARE\b', r'\bRING\b', r'\bIMPELLER\b', r'\bO-RING\b', r'\bSEAL\s*FACE\b', r'\bPART\b']
        
        has_assembly = any(re.search(kw, desc) for kw in assembly_keywords)
        has_spare = any(re.search(kw, desc) for kw in spare_keywords)
        
        if has_assembly and not has_spare:
            specs["is_kit_or_assembly"] = True
        else:
            specs["is_kit_or_assembly"] = False
            
        return specs
