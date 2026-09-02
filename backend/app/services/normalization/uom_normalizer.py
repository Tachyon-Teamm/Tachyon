import re
from typing import Tuple, Dict

# Standard UOM mappings
UOM_MAP: Dict[str, str] = {
    "NOS": "EA",
    "NO": "EA",
    "NUM": "EA",
    "NUMBERS": "EA",
    "NUMBER": "EA",
    "PCS": "EA",
    "PC": "EA",
    "PIECES": "EA",
    "PIECE": "EA",
    "EACH": "EA",
    "EA": "EA",
    "UNIT": "EA",
    "UNITS": "EA",
    
    "M": "MTR",
    "MTR": "MTR",
    "METER": "MTR",
    "METERS": "MTR",
    "METRE": "MTR",
    "METRES": "MTR",
    "LM": "MTR",
    "RMT": "MTR",
    
    "KG": "KG",
    "KGS": "KG",
    "KILOGRAM": "KG",
    "KILOGRAMS": "KG",
    
    "L": "LTR",
    "LTR": "LTR",
    "LTRS": "LTR",
    "LITER": "LTR",
    "LITERS": "LTR",
    "LITRE": "LTR",
    "LITRES": "LTR",
    
    "SET": "SET",
    "SETS": "SET",
    "KIT": "KIT",
    "KITS": "KIT",
    "PAIR": "PAIR",
    "PAIRS": "PAIR",
    
    "DRUM": "DRM",
    "DRM": "DRM",
    "BUCKET": "BKT",
    "BKT": "BKT",
    "CAN": "CAN",
    "BAG": "BAG",
    "BOX": "BOX"
}

# Regex for packaging multipliers (e.g., 18KG BUCKET, 180 KG DRUM, 200 LTR BBL)
PACKAGING_PATTERN = re.compile(
    r'(?:^|\s|-|_|\()(\d+(?:\.\d+)?)\s*(KG|KGS|LTR|LTRS|GM|GMS|ML|MTR|M|L)\b\s*(?:BUCKET|DRUM|CAN|BKT|DRM|BAG|BOX|PACK|TIN|BBL|CONTAINER|PAIL|CANISTER)?',
    re.IGNORECASE
)

class UOMNormalizer:
    @staticmethod
    def normalize_uom(raw_uom: str) -> str:
        if not raw_uom:
            return "EA"
        clean = raw_uom.strip().upper()
        return UOM_MAP.get(clean, clean)

    @staticmethod
    def extract_packaging_factor(description: str, raw_uom: str = "") -> Tuple[float, str]:
        """
        Parses descriptions like 'GREASE MOBILITH SHC 100 - 18KG BUCKET'
        Returns: (multiplier: float, base_uom: str) -> (18.0, "KG")
        """
        if not description:
            return 1.0, UOMNormalizer.normalize_uom(raw_uom)
        
        match = PACKAGING_PATTERN.search(description)
        if match:
            multiplier_val = float(match.group(1))
            unit_val = match.group(2).upper()
            
            if unit_val in ["KG", "KGS"]:
                base = "KG"
            elif unit_val in ["LTR", "LTRS", "L"]:
                base = "LTR"
            elif unit_val in ["GM", "GMS"]:
                multiplier_val = multiplier_val / 1000.0
                base = "KG"
            elif unit_val == "ML":
                multiplier_val = multiplier_val / 1000.0
                base = "LTR"
            elif unit_val in ["M", "MTR"]:
                base = "MTR"
            else:
                base = UOMNormalizer.normalize_uom(unit_val)
                
            return multiplier_val, base
            
        norm_uom = UOMNormalizer.normalize_uom(raw_uom)
        return 1.0, norm_uom
