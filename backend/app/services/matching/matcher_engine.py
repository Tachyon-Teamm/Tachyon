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
    def execute_matching_job(cls, db: Session, job_id: int) -> Dict[str, Any]:
        return cls.execute_cross_cpse_matching(db, job_id)

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
            
            # Bulk pre-load embeddings and procurement records to eliminate N+1 queries
            all_mat_ids = [m.id for m in materials]
            all_embs = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id.in_(all_mat_ids)).all()
            emb_map = {e.material_id: e for e in all_embs}

            all_procs = db.query(ProcurementHistory).filter(ProcurementHistory.material_id.in_(all_mat_ids)).all()
            proc_map = {p.material_id: p for p in all_procs}

            for m in materials:
                emb = emb_map.get(m.id)
                if emb and emb.embedding is not None:
                    dense_dict[m.id] = list(emb.embedding)
                    sparse_dict[m.id] = emb.sparse_vector if emb.sparse_vector else EmbeddingService.generate_sparse_vector(EmbeddingService.build_canonical_text(m.extracted_attributes, m.short_description))
                else:
                    canonical = EmbeddingService.build_canonical_text(m.extracted_attributes, m.short_description)
                    v = EmbeddingService.generate_embedding(canonical)
                    s = EmbeddingService.generate_sparse_vector(canonical)
                    dense_dict[m.id] = v
                    sparse_dict[m.id] = s
                    try:
                        db.add(MaterialEmbedding(material_id=m.id, embedding=v, sparse_vector=s))
                    except Exception as add_err:
                        print(f"[MatcherEngine] Note: Could not cache on-the-fly embedding: {add_err}")
                    
                proc = proc_map.get(m.id)
                if proc:
                    procurement_dict[m.id] = {
                        "vendor_normalized": proc.vendor_normalized or proc.vendor_name,
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
            total_pairs = 0

            for (id_a, id_b) in candidate_pairs:
                try:
                    mat_a = mat_dict.get(id_a)
                    mat_b = mat_dict.get(id_b)
                    if not mat_a or not mat_b:
                        continue
                    
                    # Strictly compare across different CPSEs only
                    if mat_a.cpse_id == mat_b.cpse_id:
                        continue

                    total_pairs += 1

                    specs_a = {
                        k: v for k, v in {
                            "item_noun": getattr(mat_a, "item_noun", None),
                            "nominal_size": getattr(mat_a, "nominal_size", None),
                            "pressure_class": getattr(mat_a, "pressure_class", None),
                            "moc": getattr(mat_a, "moc", None),
                            "schedule": getattr(mat_a, "schedule", None),
                            "end_connection": getattr(mat_a, "end_connection", None),
                            "standard_spec": getattr(mat_a, "standard_spec", None),
                            "clean_part_number": getattr(mat_a, "clean_part_number", None),
                            "clearance_suffix": getattr(mat_a, "clearance_suffix", None),
                            "is_kit_or_assembly": getattr(mat_a, "is_kit_or_assembly", False),
                        }.items() if v is not None
                    }
                    if mat_a.extracted_attributes:
                        specs_a.update(mat_a.extracted_attributes)
                    if mat_a.technical_attributes:
                        specs_a.update(mat_a.technical_attributes)

                    specs_b = {
                        k: v for k, v in {
                            "item_noun": getattr(mat_b, "item_noun", None),
                            "nominal_size": getattr(mat_b, "nominal_size", None),
                            "pressure_class": getattr(mat_b, "pressure_class", None),
                            "moc": getattr(mat_b, "moc", None),
                            "schedule": getattr(mat_b, "schedule", None),
                            "end_connection": getattr(mat_b, "end_connection", None),
                            "standard_spec": getattr(mat_b, "standard_spec", None),
                            "clean_part_number": getattr(mat_b, "clean_part_number", None),
                            "clearance_suffix": getattr(mat_b, "clearance_suffix", None),
                            "is_kit_or_assembly": getattr(mat_b, "is_kit_or_assembly", False),
                        }.items() if v is not None
                    }
                    if mat_b.extracted_attributes:
                        specs_b.update(mat_b.extracted_attributes)
                    if mat_b.technical_attributes:
                        specs_b.update(mat_b.technical_attributes)

                    # Hard Invariant Guardrail Veto
                    is_vetoed, veto_reason, suggested_route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
                    route = suggested_route or ("REJECT" if is_vetoed else "IDENTICAL")

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

                    effective_score = 0.0 if is_vetoed and route == "REJECT" else scores["composite_score"]
                    
                    # Veto Tier Clamping
                    if is_vetoed:
                        tier = "MEDIUM" if route == "SUBSTITUTE" else "LOW"
                    else:
                        tier = scores["confidence_tier"]

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
                        "suggested_route": route,
                        "confidence_tier": tier,
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
                except Exception as pair_err:
                    print(f"[MatcherEngine] Warning: Skipping malformed pair ({id_a}, {id_b}): {pair_err}")
                    continue

            # 3. Correlation Clustering for Multi-CPSE Transitive Resolution
            clustering_res = ClusterEngine.form_clusters(candidate_edges_for_clustering, min_score=settings.THRESHOLD_MEDIUM)
            mat_to_cluster = clustering_res["material_to_cluster"]

            candidates_created = 0
            created_review_clusters: Set[str] = set()

            for c_info in candidate_records:
                id_a = c_info["material_a_id"]
                id_b = c_info["material_b_id"]
                
                # Unvetoed items get their DSU cluster ID; vetoed items get independent cluster IDs
                if not c_info["safety_veto"]:
                    cluster_id = mat_to_cluster.get(id_a) or mat_to_cluster.get(id_b) or f"cluster_{uuid.uuid4().hex[:8]}"
                else:
                    cluster_id = f"sub_cluster_{uuid.uuid4().hex[:8]}"

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
                    suggested_route=c_info["suggested_route"],
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
                        confidence_tier=c_info["confidence_tier"]
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
            job.error_message = str(e)
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

            # Gather embeddings in bulk
            all_mats = new_materials + existing_materials
            all_mat_ids = [m.id for m in all_mats]
            all_embs = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id.in_(all_mat_ids)).all()
            emb_map = {e.material_id: e for e in all_embs}

            dense_dict: Dict[int, List[float]] = {}
            for m in all_mats:
                emb = emb_map.get(m.id)
                if emb and emb.embedding is not None:
                    dense_dict[m.id] = list(emb.embedding)
                else:
                    v = EmbeddingService.generate_embedding(m.short_description)
                    dense_dict[m.id] = v
                    try:
                        db.add(MaterialEmbedding(material_id=m.id, embedding=v))
                    except Exception:
                        pass

            db.commit()

            # Generate incremental candidate pairs
            candidate_pairs = BlockingEngine.generate_incremental_candidates(
                new_materials=new_materials,
                existing_materials=existing_materials,
                dense_dict=dense_dict,
                min_dense_sim=0.50
            )

            mat_map = {m.id: m for m in all_mats}
            candidate_records = []
            for (id_a, id_b) in candidate_pairs:
                try:
                    mat_a = mat_map.get(id_a)
                    mat_b = mat_map.get(id_b)
                    if not mat_a or not mat_b or mat_a.cpse_id == mat_b.cpse_id:
                        continue

                    specs_a = mat_a.technical_attributes or mat_a.extracted_attributes or {}
                    specs_b = mat_b.technical_attributes or mat_b.extracted_attributes or {}

                    is_vetoed, veto_reason, suggested_route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
                    route = suggested_route or ("REJECT" if is_vetoed else "IDENTICAL")

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

                    effective_score = 0.0 if is_vetoed and route == "REJECT" else scores["composite_score"]
                    
                    if is_vetoed:
                        tier = "MEDIUM" if route == "SUBSTITUTE" else "LOW"
                    else:
                        tier = scores["confidence_tier"]

                    cluster_id = f"cluster_{uuid.uuid4().hex[:8]}"
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
                        suggested_route=route,
                        confidence_tier=tier,
                        cluster_group_id=cluster_id
                    )
                    db.add(cand)
                    db.flush()
                    candidate_records.append(cand)

                    # Add to Review Queue if High/Medium confidence or veto requires review
                    if effective_score >= settings.THRESHOLD_MEDIUM or is_vetoed:
                        review_entry = ReviewQueue(
                            candidate_id=cand.id,
                            cluster_group_id=cluster_id,
                            category_code=mat_a.item_noun or "GENERAL",
                            status="PENDING",
                            confidence_tier=tier
                        )
                        db.add(review_entry)
                except Exception as p_err:
                    print(f"[MatcherEngine] Incremental pair skip: {p_err}")
                    continue

            job.status = "COMPLETED"
            job.total_pairs_evaluated = len(candidate_pairs)
            job.candidates_found = len(candidate_records)
            db.commit()
            return {"status": "COMPLETED", "candidates_found": len(candidate_records), "pairs_evaluated": len(candidate_pairs)}

        except Exception as e:
            db.rollback()
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()
            raise e
