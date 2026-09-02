try:
    import numpy as np
except ImportError:
    np = None
import re
import math
from typing import List, Dict, Any, Union, Optional, Tuple
from app.core.config import settings

class EmbeddingService:
    _dense_model = None
    _sparse_model = None
    _load_attempted: bool = False

    @classmethod
    def get_model(cls):
        if not cls._load_attempted:
            cls._load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                cls._dense_model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
            except Exception:
                try:
                    from sentence_transformers import SentenceTransformer
                    cls._dense_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
                except Exception:
                    cls._dense_model = None
        return cls._dense_model

    @staticmethod
    def build_canonical_text(specs: Optional[Dict[str, Any]] = None, raw_desc: str = "") -> str:
        """
        Synthesizes a structured, high-signal canonical text string from extracted specs
        for optimal vector encoding across disparate CPSE ERP descriptions.
        """
        if specs:
            parts = []
            # High-priority semantic anchors in standard engineering order
            if specs.get("item_noun"):
                parts.append(str(specs["item_noun"]).strip())
            if specs.get("nominal_size"):
                parts.append(str(specs["nominal_size"]).strip())
            if specs.get("pressure_class"):
                parts.append(str(specs["pressure_class"]).strip())
            if specs.get("schedule"):
                parts.append(str(specs["schedule"]).strip())
            if specs.get("moc"):
                parts.append(str(specs["moc"]).strip())
            if specs.get("end_connection"):
                parts.append(str(specs["end_connection"]).strip())
            if specs.get("standard_spec"):
                parts.append(str(specs["standard_spec"]).strip())
            if specs.get("clean_part_number"):
                parts.append(str(specs["clean_part_number"]).strip())
            elif specs.get("part_number"):
                parts.append(str(specs["part_number"]).strip())
            if specs.get("clearance_suffix"):
                parts.append(str(specs["clearance_suffix"]).strip())

            if parts:
                return ", ".join(parts)

        # Fallback to preprocessed raw text if specs are minimal
        if raw_desc:
            from app.services.normalization.domain_lexicon import DomainLexicon
            return DomainLexicon.preprocess_text(raw_desc)
        return ""

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """
        Generates a dense semantic embedding (384-d / configured EMBEDDING_DIMENSION).
        """
        if not text:
            return cls._deterministic_hash_vector("", settings.EMBEDDING_DIMENSION)

        model = cls.get_model()
        if model is not None:
            try:
                emb = model.encode(text, normalize_embeddings=True)
                emb_list = emb.tolist() if hasattr(emb, "tolist") else list(emb)
                if len(emb_list) < settings.EMBEDDING_DIMENSION:
                    emb_list = emb_list + [0.0] * (settings.EMBEDDING_DIMENSION - len(emb_list))
                elif len(emb_list) > settings.EMBEDDING_DIMENSION:
                    emb_list = emb_list[:settings.EMBEDDING_DIMENSION]
                return emb_list
            except Exception as encode_err:
                print(f"[EmbeddingService] encode fallback due to: {encode_err}")

        # Deterministic zero-dependency hashing fallback for instant testing and air-gapped environments
        return cls._deterministic_hash_vector(text, settings.EMBEDDING_DIMENSION)

    @classmethod
    def generate_batch_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """
        Generates dense semantic embeddings for a batch of strings.
        """
        if not texts:
            return []

        model = cls.get_model()
        if model is not None:
            try:
                embs = model.encode(texts, normalize_embeddings=True)
                raw_list = embs.tolist() if hasattr(embs, "tolist") else [list(x) for x in embs]
                res = []
                for emb in raw_list:
                    if len(emb) < settings.EMBEDDING_DIMENSION:
                        emb = emb + [0.0] * (settings.EMBEDDING_DIMENSION - len(emb))
                    elif len(emb) > settings.EMBEDDING_DIMENSION:
                        emb = emb[:settings.EMBEDDING_DIMENSION]
                    res.append(emb)
                return res
            except Exception as batch_err:
                print(f"[EmbeddingService] batch encode fallback due to: {batch_err}")

        return [cls._deterministic_hash_vector(t, settings.EMBEDDING_DIMENSION) for t in texts]

    @classmethod
    def generate_sparse_vector(cls, text: str) -> Dict[str, float]:
        """
        Generates an alphanumeric-preserving learned sparse representation (SPLADE-v3 / BM25 style).
        Crucial for preserving exact part numbers (e.g. '6205-2RS1', 'WNRF', '300#', 'SCH40', 'M16').
        """
        if not text:
            return {}
            
        tokens = re.findall(r'[A-Z0-9#]+(?:[-/][A-Z0-9#]+)*|\b[A-Z0-9#]+\b', text.upper())
        tf_dict: Dict[str, float] = {}
        
        for token in tokens:
            if len(token) < 2:
                continue
            # Weight alphanumeric part numbers, clearance tokens, and pressure ratings higher
            is_part_number = bool(re.search(r'\d', token) and re.search(r'[A-Z]', token))
            is_rating = bool(re.match(r'^\d+#$', token) or re.match(r'^SCH\d+$', token) or re.match(r'^M\d+$', token))
            is_clearance = token in ("C2", "C3", "C4", "2RS1", "2RS", "ZZ", "2Z")
            
            weight = 1.0
            if is_part_number:
                weight = 3.0
            elif is_rating or is_clearance:
                weight = 2.5
            elif re.match(r'^\d+$', token):
                weight = 1.5
                
            tf_dict[token] = tf_dict.get(token, 0.0) + weight
            
        # L2-normalize sparse weights
        norm = math.sqrt(sum(w * w for w in tf_dict.values()))
        if norm > 0:
            return {k: round(v / norm, 4) for k, v in tf_dict.items()}
        return tf_dict

    @staticmethod
    def compute_sparse_similarity(sparse_a: Dict[str, float], sparse_b: Dict[str, float]) -> float:
        """Computes dot product cosine similarity between two sparse term vectors."""
        if not sparse_a or not sparse_b:
            return 0.0
        dot = sum(sparse_a[k] * sparse_b[k] for k in sparse_a if k in sparse_b)
        return max(0.0, min(1.0, float(dot)))

    @staticmethod
    def compute_reciprocal_rank_fusion(
        dense_scores: Dict[int, float],
        sparse_scores: Dict[int, float],
        k: int = 60,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> Dict[int, float]:
        """
        Reciprocal Rank Fusion (RRF) combining dense semantic search and sparse lexical search:
        RRF(d) = w_dense / (k + rank_dense(d)) + w_sparse / (k + rank_sparse(d))
        """
        dense_ranked = sorted(dense_scores.keys(), key=lambda x: dense_scores[x], reverse=True)
        sparse_ranked = sorted(sparse_scores.keys(), key=lambda x: sparse_scores[x], reverse=True)
        
        dense_rank_map = {doc_id: rank + 1 for rank, doc_id in enumerate(dense_ranked)}
        sparse_rank_map = {doc_id: rank + 1 for rank, doc_id in enumerate(sparse_ranked)}
        
        all_doc_ids = set(dense_scores.keys()).union(set(sparse_scores.keys()))
        rrf_scores: Dict[int, float] = {}
        
        for doc_id in all_doc_ids:
            score = 0.0
            if doc_id in dense_rank_map:
                score += dense_weight * (1.0 / (k + dense_rank_map[doc_id]))
            if doc_id in sparse_rank_map:
                score += sparse_weight * (1.0 / (k + sparse_rank_map[doc_id]))
            rrf_scores[doc_id] = round(score, 6)
            
        return dict(sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True))

    @staticmethod
    def _deterministic_hash_vector(text: str, dim: int = 384) -> List[float]:
        """
        Deterministic pseudo-embedding for testing environments and air-gapped deployments.
        Strips punctuation, performs subword character n-gram projections, and L2-normalizes.
        """
        import hashlib
        clean_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = [w for w in clean_text.split() if w]
        if not tokens:
            vec = [0.0] * dim
            vec[0] = 1.0
            return vec

        # Subword n-grams (3-grams) for robust typo & token variant tolerance
        subwords = []
        for t in tokens:
            subwords.append(t)
            if len(t) >= 4:
                for idx in range(len(t) - 2):
                    subwords.append(t[idx:idx+3])

        if np is not None:
            vec = np.zeros(dim, dtype=np.float32)
            for item in subwords:
                h = int(hashlib.md5(item.encode('utf-8')).hexdigest(), 16)
                idx = h % dim
                val = ((h >> 8) % 1000) / 500.0 - 1.0
                vec[idx] += val
                vec[(idx + 13) % dim] += val * 0.5
                vec[(idx + 37) % dim] += val * 0.25
            
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                vec[0] = 1.0
            return vec.tolist()
        else:
            vec_list = [0.0] * dim
            for item in subwords:
                h = int(hashlib.md5(item.encode('utf-8')).hexdigest(), 16)
                idx = h % dim
                val = ((h >> 8) % 1000) / 500.0 - 1.0
                vec_list[idx] += val
                vec_list[(idx + 13) % dim] += val * 0.5
                vec_list[(idx + 37) % dim] += val * 0.25
            
            norm = math.sqrt(sum(x * x for x in vec_list))
            if norm > 0:
                vec_list = [round(x / norm, 6) for x in vec_list]
            else:
                vec_list[0] = 1.0
            return vec_list

