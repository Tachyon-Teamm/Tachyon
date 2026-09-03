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

# Regex for packaging multipliers with explicit container requirement (e.g., 18KG BUCKET, 180 KG DRUM, 200 LTR BBL)
PACKAGING_CONTAINER_PATTERN = re.compile(
    r'(?:^|\s|-|_|\()(\d+(?:\.\d+)?)\s*(KG|KGS|LTR|LTRS|GM|GMS|ML|MTR|M|L)\b\s*(BUCKET|DRUM|CAN|BKT|DRM|BAG|BOX|PACK|TIN|BBL|CONTAINER|PAIL|CANISTER)\b',
    re.IGNORECASE
)

# Regex for count-based packages (e.g. PACK OF 50 NOS, BOX OF 100)
PACKAGING_COUNT_PATTERN = re.compile(
    r'\b(?:PACK|BOX|SET|PKT|BAG)\s*(?:OF|-)?\s*(\d+)\s*(?:NOS|PCS|EA|PIECES|NUMBERS)?\b',
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
        Parses descriptions like 'GREASE MOBILITH SHC 100 - 18KG BUCKET' or 'FASTENERS PACK OF 50'
        Returns: (multiplier: float, base_uom: str) -> (18.0, "KG") or (50.0, "EA")
        """
        if not description:
            return 1.0, UOMNormalizer.normalize_uom(raw_uom)
        
        # 1. Check container-based physical packaging (18KG BUCKET, 200L DRUM)
        match = PACKAGING_CONTAINER_PATTERN.search(description)
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
            
        # 2. Check count-based packages (PACK OF 50, BOX OF 100)
        count_match = PACKAGING_COUNT_PATTERN.search(description)
        if count_match:
            multiplier_val = float(count_match.group(1))
            norm_uom = UOMNormalizer.normalize_uom(raw_uom) if raw_uom else "EA"
            return multiplier_val, norm_uom

        norm_uom = UOMNormalizer.normalize_uom(raw_uom)
        return 1.0, norm_uom
