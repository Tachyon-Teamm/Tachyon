from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.models import ReviewFeedback, Material, ReviewQueue, MatchCandidate

class ActiveLearningPipeline:
    """
    Automated Active Learning Feedback Loop:
    Harvests human steward decisions (Approve = Positive, Reject/Split = Negative)
    to generate contrastive fine-tuning triplets (Anchor, Positive, Negative)
    for scheduled model updates via MultipleNegativesRankingLoss.
    """

    @classmethod
    def harvest_contrastive_triplets(cls, db: Session, limit: int = 5000) -> List[Dict[str, Any]]:
        feedbacks = db.query(ReviewFeedback).order_by(ReviewFeedback.created_at.desc()).limit(limit).all()
        triplets = []

        for fb in feedbacks:
            mat_a = db.query(Material).filter(Material.id == fb.material_a_id).first()
            mat_b = db.query(Material).filter(Material.id == fb.material_b_id).first()
            if not mat_a or not mat_b:
                continue

            decision = fb.human_decision.upper()
            if "APPROVED" in decision or "IDENTICAL" in decision:
                triplets.append({
                    "anchor": mat_a.short_description,
                    "positive": mat_b.short_description,
                    "negative": None,
                    "label": "IDENTICAL",
                    "category": mat_a.item_noun or "GENERAL"
                })
            elif "REJECT" in decision or "SPLIT" in decision:
                triplets.append({
                    "anchor": mat_a.short_description,
                    "positive": None,
                    "negative": mat_b.short_description,
                    "label": "REJECTED_MISMATCH",
                    "category": mat_a.item_noun or "GENERAL",
                    "reason": fb.reviewer_notes
                })

        return triplets

    @classmethod
    def format_mnrl_dataset(cls, triplets: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
        """
        Pairs up (Anchor, Positive, Negative) tuples for SentenceTransformer contrastive fine-tuning.
        """
        positives: Dict[str, str] = {}
        negatives: Dict[str, str] = {}

        for t in triplets:
            anc = t["anchor"]
            if t.get("positive"):
                positives[anc] = t["positive"]
            if t.get("negative"):
                negatives[anc] = t["negative"]

        mnrl_records = []
        for anc, pos in positives.items():
            neg = negatives.get(anc, "MISCELLANEOUS NON-MATCHING INDUSTRIAL SPARE")
            mnrl_records.append((anc, pos, neg))

        return mnrl_records
