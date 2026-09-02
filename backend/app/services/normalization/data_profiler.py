import re
import math
from typing import Dict, Any, List, Optional
from collections import Counter

class DataQualityReport:
    def __init__(
        self,
        total_rows: int,
        completeness_rate: float,
        valid_uom_rate: float,
        duplicate_code_rate: float,
        spec_density_score: float,
        shannon_entropy: float,
        quality_score: float,
        recommendations: List[str]
    ):
        self.total_rows = total_rows
        self.completeness_rate = round(completeness_rate, 4)
        self.valid_uom_rate = round(valid_uom_rate, 4)
        self.duplicate_code_rate = round(duplicate_code_rate, 4)
        self.spec_density_score = round(spec_density_score, 4)
        self.shannon_entropy = round(shannon_entropy, 4)
        self.quality_score = round(quality_score, 4)
        self.is_acceptable = self.quality_score >= 0.60
        self.recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "completeness_rate": self.completeness_rate,
            "valid_uom_rate": self.valid_uom_rate,
            "duplicate_code_rate": self.duplicate_code_rate,
            "spec_density_score": self.spec_density_score,
            "shannon_entropy": self.shannon_entropy,
            "quality_score": self.quality_score,
            "is_acceptable": self.quality_score >= 0.60,
            "recommendations": self.recommendations
        }

class DataProfiler:
    """
    Automated Multi-Sector Batch Data Profiler:
    Evaluates incoming raw CPSE spreadsheets/extracts for data quality,
    completeness, UOM validity, specification density, and Shannon entropy information density.
    """

    KNOWN_UOMS = {
        "EA", "NOS", "NUMBERS", "NO", "PCS", "PC", "PIECE", "PIECES",
        "MTR", "METER", "METERS", "M", "KG", "KGS", "KILOGRAM",
        "LTR", "LITRE", "LITRES", "SET", "SETS", "BKT", "BUCKET",
        "DRM", "DRUM", "BOX", "PKT", "ROLL", "CAN", "TON", "MT", "SQM"
    }

    SPEC_INDICATORS = re.compile(
        r'\b(\d+(?:\.\d+)?\s*(?:INCH|IN|\"|MM|CM|MTR|M|KG|LTR|KV|V|VOLT|A|AMP|KA|KW|MW|HP|SCH|CLASS|CL|PN|#|M\d+|DEG|GRADE|BAR))\b',
        re.IGNORECASE
    )

    @staticmethod
    def calculate_shannon_entropy(texts: List[str]) -> float:
        """
        Calculates Shannon Entropy of word frequencies across batch descriptions:
        H(X) = -sum(p(x) * log2(p(x)))
        """
        if not texts:
            return 0.0
        words = []
        for t in texts:
            words.extend(t.upper().split())
        if not words:
            return 0.0
        total_words = len(words)
        counts = Counter(words)
        entropy = -sum((cnt / total_words) * math.log2(cnt / total_words) for cnt in counts.values())
        # Normalize to 0.0 - 1.0 (typical vocabulary entropy maxes around 12 bits)
        return min(1.0, max(0.0, entropy / 10.0))

    @classmethod
    def profile_records(cls, records: List[Dict[str, Any]]) -> DataQualityReport:
        if not records:
            return DataQualityReport(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ["No records provided for profiling."])

        total = len(records)
        complete_count = 0
        valid_uom_count = 0
        seen_codes = set()
        duplicate_code_count = 0
        spec_dense_count = 0
        all_descriptions = []

        for r in records:
            # 1. Check essential fields completeness
            code = str(r.get("material_code") or r.get("MATERIAL_NO") or r.get("code") or "").strip()
            desc = str(r.get("short_description") or r.get("ITEM_SPEC") or r.get("description") or "").strip()
            uom = str(r.get("uom") or r.get("UNIT_OF_MEASURE") or r.get("base_uom") or "").strip().upper()

            if desc:
                all_descriptions.append(desc)

            if code and desc:
                complete_count += 1

            # 2. Check UOM validity
            if uom in cls.KNOWN_UOMS:
                valid_uom_count += 1

            # 3. Duplicate code check within batch
            if code:
                if code in seen_codes:
                    duplicate_code_count += 1
                else:
                    seen_codes.add(code)

            # 4. Specification density (presence of ratings, sizes, units)
            if desc and cls.SPEC_INDICATORS.search(desc):
                spec_dense_count += 1

        completeness_rate = complete_count / total
        valid_uom_rate = valid_uom_count / total
        duplicate_code_rate = duplicate_code_count / total
        spec_density = spec_dense_count / total
        entropy_score = cls.calculate_shannon_entropy(all_descriptions)

        # Composite Quality Score calculation
        quality_score = max(0.0, min(1.0, (
            0.35 * completeness_rate +
            0.20 * valid_uom_rate +
            0.25 * spec_density +
            0.10 * entropy_score +
            0.10 * (1.0 - duplicate_code_rate)
        )))

        recommendations = []
        if completeness_rate < 0.90:
            recommendations.append(f"High missing field rate: {round((1.0 - completeness_rate) * 100, 1)}% rows missing material code or description.")
        if valid_uom_rate < 0.80:
            recommendations.append(f"Non-standard UOM rate: {round((1.0 - valid_uom_rate) * 100, 1)}% rows have invalid or unmapped UOMs.")
        if duplicate_code_rate > 0.05:
            recommendations.append(f"Duplicate material code rate is high ({round(duplicate_code_rate * 100, 1)}%). Ensure batch has unique local codes.")
        if spec_density < 0.70:
            recommendations.append(f"Low specification density: {round((1.0 - spec_density) * 100, 1)}% descriptions lack clear dimensional or technical parameters.")
        if entropy_score < 0.30:
            recommendations.append("Low description vocabulary diversity: Input contains repetitive or generic descriptions.")
        if not recommendations:
            recommendations.append("Batch data quality meets enterprise standards for automated processing.")

        return DataQualityReport(
            total_rows=total,
            completeness_rate=completeness_rate,
            valid_uom_rate=valid_uom_rate,
            duplicate_code_rate=duplicate_code_rate,
            spec_density_score=spec_density,
            shannon_entropy=entropy_score,
            quality_score=quality_score,
            recommendations=recommendations
        )
