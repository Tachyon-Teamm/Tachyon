import re
from typing import Dict

# Multi-Sector Engineering Lexicons (Oil & Gas, Power, Steel, Mining, Electrical)
COLLOQUIAL_TERMS: Dict[str, str] = {
    # Oil & Gas / Refinery
    r"\bJAALI\s*WALA\b": "SPIRAL WOUND",
    r"\bJALI\s*WALA\b": "SPIRAL WOUND",
    r"\bJALIWALA\b": "SPIRAL WOUND",
    r"\bCHURI\b": "THREADED",
    r"\bCHOODI\b": "THREADED",
    r"\bDORI\b": "GLAND PACKING ROPE",
    r"\bVLV\b": "VALVE",
    r"\bVALV\b": "VALVE",
    r"\bFLG\b": "FLANGE",
    r"\bFLNG\b": "FLANGE",
    r"\bSMLS\b": "SEAMLESS",
    r"\bSEAMLES\b": "SEAMLESS",
    r"\bCS\b": "CARBON STEEL",
    r"\bCARBON\s*STL\b": "CARBON STEEL",
    r"\bSS\b": "STAINLESS STEEL",
    r"\bSTAINLESS\s*STL\b": "STAINLESS STEEL",
    r"\bBRG\b": "BEARING",
    r"\bMECH\s*SEAL\b": "MECHANICAL SEAL",
    r"\bASSY\b": "ASSEMBLY",
    r"\bCARTRG\b": "CARTRIDGE",
    r"\bTEMP\b": "TEMPERATURE",
    r"\bPRESS\b": "PRESSURE",
    r"\bWCB\b": "ASTM A216 WCB",
    r"\bSCH\b": "SCHEDULE",
    
    # Power & Electrical
    r"\bXFRMR\b": "TRANSFORMER",
    r"\bTRANSF\b": "TRANSFORMER",
    r"\bSWGR\b": "SWITCHGEAR",
    r"\bINSLTR\b": "INSULATOR",
    r"\bCBL\b": "CABLE",
    r"\bCONTR\b": "CONTACTOR",
    r"\bRLY\b": "RELAY",
    r"\bCKT\s*BRKR\b": "CIRCUIT BREAKER",
    r"\bLT\s*CABLE\b": "LOW TENSION CABLE",
    r"\bHT\s*CABLE\b": "HIGH TENSION CABLE",
    
    # Steel & Heavy Engineering
    r"\bTMT\b": "THERMO MECHANICALLY TREATED STEEL BAR",
    r"\bBLT\b": "BOLT",
    r"\bFASTNR\b": "FASTENER",
    r"\bSTRUC\s*STL\b": "STRUCTURAL STEEL",
    
    # Mining & Material Handling
    r"\bCVYR\b": "CONVEYOR",
    r"\bHYD\b": "HYDRAULIC",
    r"\bPMP\b": "PUMP",
    r"\bGRBX\b": "GEARBOX"
}

# Equivalent Engineering Standards Dictionary across sectors
STANDARDS_EQUIVALENCE: Dict[str, str] = {
    # Piping & Valves (ASME / ANSI / API / BS / ISO)
    "ANSI B16.5": "ASME B16.5",
    "ANSI B16.34": "ASME B16.34",
    "ANSI B16.10": "ASME B16.10",
    "ANSI B16.9": "ASME B16.9",
    "ANSI B16.11": "ASME B16.11",
    "ANSI B16.20": "ASME B16.20",
    "API 6D": "ISO 14313",
    "BS 5351": "ISO 17292",
    "BS 1873": "BS 1873",
    "BS 1868": "BS 1868",
    
    # Steel & Construction Standards (IS / ASTM)
    "IS 2062": "IS 2062 (STRUCTURAL STEEL)",
    "IS 1786": "IS 1786 (HIGH STRENGTH DEFORMED STEEL BARS)",
    
    # Electrical Standards (IEC / IS)
    "IS 7098": "IS 7098 (XLPE INSULATED CABLES)",
    "IEC 60947": "IEC 60947 (LOW-VOLTAGE SWITCHGEAR)"
}

class DomainLexicon:
    @staticmethod
    def preprocess_text(text: str, sector: str = "GENERAL") -> str:
        if not text:
            return ""
        
        result = text.upper()
        
        # Replace colloquial phrases & abbreviations across sectors
        for pattern, standard in COLLOQUIAL_TERMS.items():
            result = re.sub(pattern, standard, result, flags=re.IGNORECASE)
            
        # Standardize whitespace and punctuation
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    @staticmethod
    def normalize_standard(std_str: str) -> str:
        if not std_str:
            return ""
        clean = std_str.strip().upper()
        return STANDARDS_EQUIVALENCE.get(clean, clean)
