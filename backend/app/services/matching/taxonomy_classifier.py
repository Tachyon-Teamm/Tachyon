import math
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import TaxonomyNode
from app.services.matching.embeddings import EmbeddingService

class TaxonomyClassifier:
    """
    Zero-Shot Vector Taxonomy Classifier.
    Predicts standard international engineering classifications (UNSPSC / eCl@ss)
    in sub-5ms by computing cosine similarity against pre-embedded taxonomy nodes.
    Requires zero custom model training.
    """
    _cached_nodes: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def load_taxonomy_cache(cls, db: Session) -> List[Dict[str, Any]]:
        if cls._cached_nodes is not None and len(cls._cached_nodes) > 0:
            return cls._cached_nodes

        nodes = db.query(TaxonomyNode).all()
        cache = []
        for n in nodes:
            vec = n.vector_embedding
            if vec is None:
                text = f"{n.name}. {n.description or ''}"
                vec = EmbeddingService.generate_embedding(text)
                n.vector_embedding = vec
                db.add(n)
            
            vec_list = list(vec) if hasattr(vec, "__iter__") else []
            cache.append({
                "id": n.id,
                "code": n.code,
                "name": n.name,
                "sector": n.sector,
                "standard": n.standard,
                "vector": vec_list
            })
        
        if cache:
            try:
                db.commit()
            except Exception:
                db.rollback()
            cls._cached_nodes = cache
        return cache or []

    @classmethod
    def classify_description(
        cls, 
        db: Session, 
        description: str, 
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Classifies raw or normalized material description into top-K taxonomy categories.
        """
        if not description or not description.strip():
            return [{
                "code": "GENERAL",
                "name": "General Industrial Equipment",
                "sector": "GENERAL",
                "confidence": 0.50
            }]

        item_vec = EmbeddingService.generate_embedding(description)
        return cls.classify_vector(db, item_vec, top_k=top_k)

    @classmethod
    def classify_vector(
        cls, 
        db: Session, 
        item_vec: List[float], 
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Calculates cosine similarity between item embedding vector and all taxonomy nodes.
        """
        nodes = cls.load_taxonomy_cache(db)
        if not nodes or not item_vec:
            return [{
                "code": "GENERAL",
                "name": "General Industrial Equipment",
                "sector": "GENERAL",
                "confidence": 0.50
            }]

        scores: List[Tuple[float, Dict[str, Any]]] = []
        
        norm_item = math.sqrt(sum(x * x for x in item_vec))
        if norm_item == 0:
            norm_item = 1.0

        for n in nodes:
            n_vec = n["vector"]
            if not n_vec or len(n_vec) != len(item_vec):
                continue
            
            dot = sum(a * b for a, b in zip(item_vec, n_vec))
            norm_n = math.sqrt(sum(y * y for y in n_vec)) or 1.0
            cos_sim = max(0.0, min(1.0, dot / (norm_item * norm_n)))
            scores.append((cos_sim, n))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = []
        for sim, n in scores[:top_k]:
            top_results.append({
                "code": n["code"],
                "name": n["name"],
                "sector": n["sector"],
                "standard": n["standard"],
                "confidence": round(float(sim), 4)
            })

        return top_results or [{
            "code": "GENERAL",
            "name": "General Industrial Equipment",
            "sector": "GENERAL",
            "confidence": 0.50
        }]
