from typing import List, Dict, Any, Optional, Tuple, Set
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.core.config import settings
from app.models.models import (
    Material, MaterialEmbedding, ProcurementHistory, MatchJob,
    MatchCandidate, ReviewQueue
)
from app.services.matching.embeddings import EmbeddingService
from app.services.matching.guardrails import SafetyGuardrails
from app.services.matching.scorer import CompositeScorer
from app.services.matching.cluster_engine import ClusterEngine

class MatcherEngine:
    @classmethod
    def execute_cross_cpse_matching(cls, db: Session, job_id: int) -> Dict[str, Any]:
        """
        Executes Two-Stage Hybrid Neuro-Symbolic Multi-CPSE Matching:
          Stage 1: Fast Hybrid Candidate Retrieval (Dense BGE-M3 + Sparse SPLADE via Reciprocal Rank Fusion)
          Stage 2: Deterministic Multi-Sector Invariant Verification + Cross-Encoder Reranking
          Stage 3: Correlation Graph Entity Resolution
        """
        job = db.query(MatchJob).filter(MatchJob.id == job_id).first()
        if not job:
            return {"status": "FAILED", "error": "Job not found"}
            
        job.status = "RUNNING"
        db.commit()
        
        try:
            # 1. Fetch active materials across all CPSEs
            materials = db.query(Material).filter(Material.status == "ACTIVE").all()
            if not materials or len(materials) < 2:
                job.status = "COMPLETED"
                job.total_pairs_evaluated = 0
                job.candidates_found = 0
                db.commit()
                return {"status": "COMPLETED", "candidates_found": 0}
                
            mat_dict: Dict[int, Material] = {m.id: m for m in materials}
            dense_dict: Dict[int, List[float]] = {}
            sparse_dict: Dict[int, Dict[str, float]] = {}
            procurement_dict: Dict[int, Dict[str, Any]] = {}
            
            for m in materials:
                emb = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == m.id).first()
                if emb and emb.embedding is not None:
                    dense_dict[m.id] = list(emb.embedding)
                    sparse_dict[m.id] = emb.sparse_vector if emb.sparse_vector else EmbeddingService.generate_sparse_vector(m.short_description)
                else:
                    v = EmbeddingService.generate_embedding(m.short_description)
                    s = EmbeddingService.generate_sparse_vector(m.short_description)
                    dense_dict[m.id] = v
                    sparse_dict[m.id] = s
                    db.add(MaterialEmbedding(material_id=m.id, embedding=v, sparse_vector=s))
                    
                proc = db.query(ProcurementHistory).filter(ProcurementHistory.material_id == m.id).first()
                if proc:
                    procurement_dict[m.id] = {
                        "vendor_normalized": proc.vendor_normalized,
                        "unit_price": proc.unit_price,
                        "hsn_code": proc.hsn_code
                    }
                else:
                    procurement_dict[m.id] = {}

            db.commit()

            # 2. 4-Tier Multi-Index High-Recall Candidate Blocking
            from app.services.matching.blocking_engine import BlockingEngine
            candidate_pairs = BlockingEngine.generate_candidate_pairs(
                materials=materials,
                dense_dict=dense_dict,
                sparse_dict=sparse_dict,
                min_dense_sim=0.50
            )

            candidate_records = []
            candidate_edges_for_clustering = []
            total_pairs = len(candidate_pairs)

            for (id_a, id_b) in candidate_pairs:
                mat_a = mat_dict.get(id_a)
                mat_b = mat_dict.get(id_b)
                if not mat_a or not mat_b:
                    continue
                if mat_a.cpse_id == mat_b.cpse_id and mat_a.material_code == mat_b.material_code:
                    continue

                specs_a = mat_a.technical_attributes or mat_a.extracted_attributes or {}
                specs_b = mat_b.technical_attributes or mat_b.extracted_attributes or {}

                # Hard Invariant Guardrail Veto
                is_vetoed, veto_reason, suggested_route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)

                # Composite Scoring with Category Weights & Dynamic Normalization
                scores = CompositeScorer.compute_composite(
                    vec_a=dense_dict.get(id_a, []),
                    vec_b=dense_dict.get(id_b, []),
                    specs_a=specs_a,
                    specs_b=specs_b,
                    proc_a=procurement_dict.get(id_a, {}),
                    proc_b=procurement_dict.get(id_b, {}),
                    category=mat_a.item_noun,
                    sparse_a=sparse_dict.get(id_a, {}),
                    sparse_b=sparse_dict.get(id_b, {}),
                    desc_a=mat_a.short_description,
                    desc_b=mat_b.short_description
                )

                effective_score = 0.0 if is_vetoed and suggested_route == "REJECT" else scores["composite_score"]

                candidate_info = {
                    "job_id": job.id,
                    "material_a_id": id_a,
                    "material_b_id": id_b,
                    "semantic_score": scores["semantic_score"],
                    "attribute_score": scores["attribute_score"],
                    "procurement_score": scores["procurement_score"],
                    "composite_score": effective_score,
                    "safety_veto": is_vetoed,
                    "veto_reason": veto_reason,
                    "confidence_tier": "LOW" if is_vetoed else scores["confidence_tier"],
                    "is_auto_approvable": scores.get("is_auto_approvable", False) and not is_vetoed,
                    "category_code": mat_a.item_noun or "GENERAL"
                }
                candidate_records.append(candidate_info)
                candidate_edges_for_clustering.append({
                    "material_a_id": id_a,
                    "material_b_id": id_b,
                    "composite_score": effective_score,
                    "is_vetoed": is_vetoed
                })

            # 3. Correlation Clustering for Multi-CPSE Transitive Resolution
            clustering_res = ClusterEngine.form_clusters(candidate_edges_for_clustering, min_score=settings.THRESHOLD_MEDIUM)
            mat_to_cluster = clustering_res["material_to_cluster"]

            candidates_created = 0
            created_review_clusters: Set[str] = set()

            for c_info in candidate_records:
                id_a = c_info["material_a_id"]
                id_b = c_info["material_b_id"]
                cluster_id = mat_to_cluster.get(id_a) or mat_to_cluster.get(id_b) or f"cluster_{uuid.uuid4().hex[:8]}"

                cand = MatchCandidate(
                    job_id=c_info["job_id"],
                    material_a_id=id_a,
                    material_b_id=id_b,
                    semantic_score=c_info["semantic_score"],
                    attribute_score=c_info["attribute_score"],
                    procurement_score=c_info["procurement_score"],
                    composite_score=c_info["composite_score"],
                    safety_veto=c_info["safety_veto"],
                    veto_reason=c_info["veto_reason"],
                    confidence_tier=c_info["confidence_tier"],
                    cluster_group_id=cluster_id
                )
                db.add(cand)
                db.flush()
                candidates_created += 1

                # Add to Review Queue if High/Medium confidence or veto requires review
                if (c_info["composite_score"] >= settings.THRESHOLD_MEDIUM or c_info["safety_veto"]) and cluster_id not in created_review_clusters:
                    created_review_clusters.add(cluster_id)
                    review_entry = ReviewQueue(
                        candidate_id=cand.id,
                        cluster_group_id=cluster_id,
                        category_code=c_info["category_code"],
                        status="PENDING",
                        confidence_tier="HIGH" if c_info["composite_score"] >= settings.THRESHOLD_HIGH and not c_info["safety_veto"] else "MEDIUM"
                    )
                    db.add(review_entry)

            job.status = "COMPLETED"
            job.total_pairs_evaluated = total_pairs
            job.candidates_found = candidates_created
            db.commit()
            return {"status": "COMPLETED", "candidates_found": candidates_created, "pairs_evaluated": total_pairs, "clusters_formed": len(created_review_clusters)}
            
        except Exception as e:
            db.rollback()
            job.status = "FAILED"
            db.commit()
            raise e

    @classmethod
    def execute_incremental_matching(
        cls,
        db: Session,
        new_material_ids: List[int],
        job_id: int
    ) -> Dict[str, Any]:
        """
        Incremental Multi-CPSE Candidate Matching:
        Efficiently evaluates only new materials against existing catalog in O(log N).
        """
        from app.services.matching.blocking_engine import BlockingEngine

        job = db.query(MatchJob).filter(MatchJob.id == job_id).first()
        if not job:
            return {"status": "FAILED", "error": "Job not found"}

        job.status = "RUNNING"
        db.commit()

        try:
            new_materials = db.query(Material).filter(Material.id.in_(new_material_ids)).all()
            existing_materials = db.query(Material).filter(
                Material.id.notin_(new_material_ids),
                Material.status == "ACTIVE"
            ).all()

            if not new_materials or not existing_materials:
                job.status = "COMPLETED"
                db.commit()
                return {"status": "COMPLETED", "candidates_found": 0}

            # Gather embeddings
            dense_dict: Dict[int, List[float]] = {}
            for m in new_materials + existing_materials:
                emb = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == m.id).first()
                if emb and emb.embedding is not None:
                    dense_dict[m.id] = list(emb.embedding)
                else:
                    v = EmbeddingService.generate_embedding(m.short_description)
                    dense_dict[m.id] = v
                    db.add(MaterialEmbedding(material_id=m.id, embedding=v))

            db.commit()

            # Generate incremental candidate pairs
            candidate_pairs = BlockingEngine.generate_incremental_candidates(
                new_materials=new_materials,
                existing_materials=existing_materials,
                dense_dict=dense_dict,
                min_dense_sim=0.50
            )

            candidate_records = []
            for (id_a, id_b) in candidate_pairs:
                mat_a = db.query(Material).filter(Material.id == id_a).first()
                mat_b = db.query(Material).filter(Material.id == id_b).first()
                if not mat_a or not mat_b:
                    continue

                specs_a = mat_a.technical_attributes or mat_a.extracted_attributes or {}
                specs_b = mat_b.technical_attributes or mat_b.extracted_attributes or {}

                is_vetoed, veto_reason, suggested_route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
                scores = CompositeScorer.compute_composite(
                    vec_a=dense_dict.get(id_a, []),
                    vec_b=dense_dict.get(id_b, []),
                    specs_a=specs_a,
                    specs_b=specs_b,
                    proc_a={},
                    proc_b={},
                    category=mat_a.item_noun,
                    desc_a=mat_a.short_description,
                    desc_b=mat_b.short_description
                )

                effective_score = 0.0 if is_vetoed and suggested_route == "REJECT" else scores["composite_score"]
                cand = MatchCandidate(
                    job_id=job.id,
                    material_a_id=id_a,
                    material_b_id=id_b,
                    semantic_score=scores["semantic_score"],
                    attribute_score=scores["attribute_score"],
                    procurement_score=scores["procurement_score"],
                    composite_score=effective_score,
                    safety_veto=is_vetoed,
                    veto_reason=veto_reason,
                    confidence_tier="LOW" if is_vetoed else scores["confidence_tier"],
                    cluster_group_id=f"cluster_{uuid.uuid4().hex[:8]}"
                )
                db.add(cand)
                candidate_records.append(cand)

            job.status = "COMPLETED"
            job.total_pairs_evaluated = len(candidate_pairs)
            job.candidates_found = len(candidate_records)
            db.commit()
            return {"status": "COMPLETED", "candidates_found": len(candidate_records), "pairs_evaluated": len(candidate_pairs)}

        except Exception as e:
            db.rollback()
            job.status = "FAILED"
            db.commit()
            raise e
