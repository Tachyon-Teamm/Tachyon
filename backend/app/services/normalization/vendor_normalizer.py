import re
from typing import Dict

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

VENDOR_ALIASES: Dict[str, str] = {
    "L&T": "LARSEN & TOUBRO",
    "L&T VALVES": "LARSEN & TOUBRO",
    "L&T VALVES LTD": "LARSEN & TOUBRO",
    "LARSEN & TOUBRO": "LARSEN & TOUBRO",
    "LARSEN & TOUBRO LTD": "LARSEN & TOUBRO",
    "LARSEN & TOUBRO LTD - VALVE DIV": "LARSEN & TOUBRO",
    "AUDCO INDIA": "LARSEN & TOUBRO",
    "AUDCO INDIA / L&T": "LARSEN & TOUBRO",
    
    "BHEL": "BHARAT HEAVY ELECTRICALS LTD",
    "BHARAT HEAVY ELECTRICALS": "BHARAT HEAVY ELECTRICALS LTD",
    
    "EIL": "ENGINEERS INDIA LTD",
    "ENGINEERS INDIA": "ENGINEERS INDIA LTD",
    
    "MICROFINISH": "MICROFINISH VALVES",
    "MICRO FINISH": "MICROFINISH VALVES",
    "MICROFINISH VALVES PVT LTD": "MICROFINISH VALVES",
    
    "FLOWSERVE": "FLOWSERVE",
    "FLOWSERVE SANMAR": "FLOWSERVE",
    "FLOWSERVE INDIA": "FLOWSERVE",
    
    "SKF": "SKF",
    "SKF INDIA": "SKF",
    "SKF BEARINGS": "SKF",
    
    "FAG": "SCHAEFFLER (FAG)",
    "FAG BEARINGS": "SCHAEFFLER (FAG)",
    "SCHAEFFLER": "SCHAEFFLER (FAG)",
    
    "KIRLOSKAR": "KIRLOSKAR BROTHERS LTD",
    "KIRLOSKAR BROTHERS": "KIRLOSKAR BROTHERS LTD",
    
    "EXXONMOBIL": "EXXONMOBIL",
    "MOBIL": "EXXONMOBIL",
    "MOBIL OIL": "EXXONMOBIL",
    "INDIAN OIL LUBES": "SERVO (IOCL)",
    "SERVO": "SERVO (IOCL)",
    "MAK LUBRICANTS": "MAK (BPCL)",
    "MAK": "MAK (BPCL)"
}

class VendorNormalizer:
    @staticmethod
    def normalize_vendor(raw_vendor: str) -> str:
        if not raw_vendor:
            return "UNKNOWN VENDOR"
            
        clean = raw_vendor.strip().upper()
        # Direct dictionary check
        if clean in VENDOR_ALIASES:
            return VENDOR_ALIASES[clean]
            
        # Word-boundary regex matching sorted by descending key length
        sorted_aliases = sorted(VENDOR_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
        for alias_key, standard_name in sorted_aliases:
            if re.search(r'\b' + re.escape(alias_key) + r'\b', clean):
                return standard_name
                
        if HAS_RAPIDFUZZ:
            match = process.extractOne(clean, list(VENDOR_ALIASES.keys()), scorer=fuzz.token_set_ratio)
            if match and match[1] >= 85:
                return VENDOR_ALIASES[match[0]]
        else:
            close = difflib.get_close_matches(clean, list(VENDOR_ALIASES.keys()), n=1, cutoff=0.7)
            if close:
                return VENDOR_ALIASES[close[0]]
            
        return clean
