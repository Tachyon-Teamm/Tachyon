import math
from typing import Dict, Any, List, Optional
from app.core.config import settings

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

class CompositeScorer:
    """
    100% Explainable Formula-Based Composite Scorer.
    Zero ML black boxes.
    Score = 0.40(Semantic) + 0.35(Parametric Specs) + 0.25(Procurement Graph)
    """

    @staticmethod
    def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
            
        if HAS_NUMPY:
            a = np.array(vec_a, dtype=np.float32)
            b = np.array(vec_b, dtype=np.float32)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            dot = np.dot(a, b)
            cos_sim = float(dot / (norm_a * norm_b))
        else:
            dot = sum(x * y for x, y in zip(vec_a, vec_b))
            norm_a = math.sqrt(sum(x * x for x in vec_a))
            norm_b = math.sqrt(sum(y * y for y in vec_b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            cos_sim = dot / (norm_a * norm_b)

        return max(0.0, min(1.0, (cos_sim + 1.0) / 2.0 if cos_sim < 0 else cos_sim))

    @staticmethod
    def calculate_attribute_overlap(specs_a: Dict[str, Any], specs_b: Dict[str, Any]) -> float:
        """
        Calculates weighted Jaccard overlap on parametric extracted attributes.
        """
        weights = {
            "clean_part_number": 0.40,
            "item_noun": 0.30,
            "nominal_size": 0.25,
            "pressure_class": 0.20,
            "moc": 0.15,
            "end_connection": 0.05,
            "schedule": 0.05
        }
        
        total_weight = 0.0
        matched_weight = 0.0
        
        for field, weight in weights.items():
            val_a = specs_a.get(field)
            val_b = specs_b.get(field)
            
            # If both records have this attribute present
            if val_a and val_b:
                total_weight += weight
                if str(val_a).strip().upper() == str(val_b).strip().upper():
                    matched_weight += weight
            elif not val_a and not val_b:
                # Neutral: both missing this spec (e.g. schedule for valves, or part_no for pipes)
                continue
            else:
                # One has it, one doesn't
                total_weight += weight
                
        if total_weight == 0:
            return 0.70 # Default base attribute score if minimal specs
            
        return float(matched_weight / total_weight)

    @staticmethod
    def calculate_procurement_score(proc_a: Dict[str, Any], proc_b: Dict[str, Any]) -> float:
        score = 0.0
        
        # 1. Vendor Match
        v_a = proc_a.get("vendor_normalized")
        v_b = proc_b.get("vendor_normalized")
        if v_a and v_b and v_a != "UNKNOWN VENDOR" and v_b != "UNKNOWN VENDOR":
            if v_a.upper() == v_b.upper():
                score += 0.50
            else:
                score += 0.10
        else:
            score += 0.25 # Neutral baseline if vendor data not provided
            
        # 2. Price Band Check (+/- 20%)
        p_a_raw = proc_a.get("unit_price")
        p_b_raw = proc_b.get("unit_price")
        try:
            p_a = float(p_a_raw) if p_a_raw is not None else 0.0
        except (ValueError, TypeError):
            p_a = 0.0
            
        try:
            p_b = float(p_b_raw) if p_b_raw is not None else 0.0
        except (ValueError, TypeError):
            p_b = 0.0

        if p_a > 0 and p_b > 0:
            ratio = min(p_a, p_b) / max(p_a, p_b)
            if ratio >= 0.80:
                score += 0.30
            elif ratio >= 0.60:
                score += 0.15
        else:
            score += 0.15 # Neutral baseline
            
        # 3. HSN Code Match
        hsn_a = proc_a.get("hsn_code")
        hsn_b = proc_b.get("hsn_code")
        if hsn_a and hsn_b:
            if str(hsn_a).strip() == str(hsn_b).strip():
                score += 0.20
        else:
            score += 0.10
            
        return min(1.0, max(0.0, score))

    @classmethod
    def compute_composite(
        cls,
        vec_a: List[float],
        vec_b: List[float],
        specs_a: Dict[str, Any],
        specs_b: Dict[str, Any],
        proc_a: Dict[str, Any],
        proc_b: Dict[str, Any],
        weight_sem: float = 0.40,
        weight_attr: float = 0.35,
        weight_proc: float = 0.25
    ) -> Dict[str, Any]:
        """
        Executes the composite formula:
        Score = 0.40(S_sem) + 0.35(S_attr) + 0.25(S_proc)
        """
        s_sem = cls.calculate_cosine_similarity(vec_a, vec_b) if vec_a and vec_b else 0.0
        s_attr = cls.calculate_attribute_overlap(specs_a, specs_b)
        s_proc = cls.calculate_procurement_score(proc_a, proc_b)

        composite = (weight_sem * s_sem) + (weight_attr * s_attr) + (weight_proc * s_proc)
        composite = round(min(1.0, max(0.0, composite)), 4)

        # Confidence Tier Routing
        tier = "LOW"
        if composite >= getattr(settings, "THRESHOLD_HIGH", 0.90):
            tier = "HIGH"
        elif composite >= getattr(settings, "THRESHOLD_MEDIUM", 0.70):
            tier = "MEDIUM"

        return {
            "composite_score": composite,
            "semantic_score": round(s_sem, 4),
            "attribute_score": round(s_attr, 4),
            "procurement_score": round(s_proc, 4),
            "confidence_tier": tier,
            "weights": {
                "semantic": weight_sem,
                "attribute": weight_attr,
                "procurement": weight_proc
            }
        }
