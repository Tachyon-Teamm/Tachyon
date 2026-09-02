import re
from typing import Dict

# Indian Refinery & Oil/Gas colloquial terms -> Standard Engineering terms
COLLOQUIAL_TERMS: Dict[str, str] = {
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
    r"\bPRESS\b": "PRESSURE"
}

# Equivalent Engineering Standards Dictionary
STANDARDS_EQUIVALENCE: Dict[str, str] = {
    "ANSI B16.5": "ASME B16.5",
    "ANSI B16.34": "ASME B16.34",
    "ANSI B16.10": "ASME B16.10",
    "ANSI B16.9": "ASME B16.9",
    "ANSI B16.11": "ASME B16.11",
    "ANSI B16.20": "ASME B16.20",
    "API 6D": "ISO 14313",
    "BS 5351": "ISO 17292",
    "BS 1873": "BS 1873",
    "BS 1868": "BS 1868"
}

class DomainLexicon:
    @staticmethod
    def preprocess_text(text: str) -> str:
        if not text:
            return ""
        
        result = text.upper()
        
        # Replace colloquial Indian plant phrases
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
