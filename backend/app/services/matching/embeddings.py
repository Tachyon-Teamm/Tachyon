import numpy as np
from typing import List, Union
from app.core.config import settings

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"[EmbeddingService] Warning: Could not load sentence-transformers model ({e}). Using deterministic fallback.")
                cls._model = None
        return cls._model

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """
        Generates a 384-dimensional embedding for text.
        Zero ML training or fine-tuning required.
        """
        model = cls.get_model()
        if model is not None:
            emb = model.encode(text, normalize_embeddings=True)
            return emb.tolist()
        
        # Deterministic zero-dependency hashing fallback for instant testing
        return cls._deterministic_hash_vector(text, settings.EMBEDDING_DIMENSION)

    @classmethod
    def generate_batch_embeddings(cls, texts: List[str]) -> List[List[float]]:
        model = cls.get_model()
        if model is not None:
            embs = model.encode(texts, normalize_embeddings=True)
            return embs.tolist()
            
        return [cls._deterministic_hash_vector(t, settings.EMBEDDING_DIMENSION) for t in texts]

    @staticmethod
    def _deterministic_hash_vector(text: str, dim: int = 384) -> List[float]:
        """Deterministic pseudo-embedding for testing environments without PyTorch weights"""
        import hashlib
        words = text.lower().split()
        vec = np.zeros(dim, dtype=np.float32)
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 1000) / 500.0 - 1.0
            vec[idx] += val
            vec[(idx + 13) % dim] += val * 0.5
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()
