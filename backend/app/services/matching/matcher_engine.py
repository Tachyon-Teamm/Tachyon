from typing import List, Dict, Any, Optional, Tuple
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

class MatcherEngine:
    @classmethod
    def execute_cross_cpse_matching(cls, db: Session, job_id: int) -> Dict[str, Any]:
        """
        Executes zero-training neuro-symbolic multi-CPSE matching.
        """
        job = db.query(MatchJob).filter(MatchJob.id == job_id).first()
        if not job:
            return {"status": "FAILED", "error": "Job not found"}
            
        job.status = "RUNNING"
        db.commit()
        
        try:
            # 1. Fetch active materials across all CPSEs with their embeddings
            materials = db.query(Material).filter(Material.status == "ACTIVE").all()
            if not materials or len(materials) < 2:
                job.status = "COMPLETED"
                job.total_pairs_evaluated = 0
                job.candidates_found = 0
                db.commit()
                return {"status": "COMPLETED", "candidates_found": 0}
                
            # Pre-load embeddings and procurement history into memory for efficient processing
            mat_dict: Dict[int, Material] = {m.id: m for m in materials}
            embeddings_dict: Dict[int, List[float]] = {}
            procurement_dict: Dict[int, Dict[str, Any]] = {}
            
            for m in materials:
                emb = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == m.id).first()
                if emb and emb.embedding is not None:
                    embeddings_dict[m.id] = list(emb.embedding)
                else:
                    # Generate embedding on the fly if missing
                    v = EmbeddingService.generate_embedding(m.short_description)
                    embeddings_dict[m.id] = v
                    
                proc = db.query(ProcurementHistory).filter(ProcurementHistory.material_id == m.id).first()
                if proc:
                    procurement_dict[m.id] = {
                        "vendor_normalized": proc.vendor_normalized,
                        "unit_price": proc.unit_price,
                        "hsn_code": proc.hsn_code
                    }
                else:
                    procurement_dict[m.id] = {}

            # 2. Level-1 Category / Noun Blocking to prevent NxN explosion
            # Group materials by normalized item noun or clean part number
            blocks: Dict[str, List[int]] = {}
            for m in materials:
                # Primary blocking key: item_noun or cleaned bearing part number
                if m.clean_part_number and len(m.clean_part_number) >= 4:
                    key = f"PART_{m.clean_part_number[:4]}"
                elif m.item_noun:
                    key = f"NOUN_{m.item_noun}"
                else:
                    key = "NOUN_GENERAL"
                    
                if key not in blocks:
                    blocks[key] = []
                blocks[key].append(m.id)

            total_pairs = 0
            candidates_created = 0
            clusters_map: Dict[str, str] = {} # Keyed by normalized canonical spec signature

            # 3. Evaluate pairs within blocks across different CPSEs
            for block_key, mat_ids in blocks.items():
                for i in range(len(mat_ids)):
                    for j in range(i + 1, len(mat_ids)):
                        id_a = mat_ids[i]
                        id_b = mat_ids[j]
                        mat_a = mat_dict[id_a]
                        mat_b = mat_dict[id_b]
                        
                        # Only match across different CPSEs or distinct materials
                        if mat_a.cpse_id == mat_b.cpse_id and mat_a.material_code == mat_b.material_code:
                            continue
                            
                        total_pairs += 1
                        specs_a = mat_a.extracted_attributes or {}
                        specs_b = mat_b.extracted_attributes or {}
                        
                        # Apply Hard Deterministic Invariant Safety Guardrail Veto
                        is_vetoed, veto_reason, suggested_route = SafetyGuardrails.evaluate_pair(specs_a, specs_b)
                        
                        vec_a = embeddings_dict.get(id_a, [])
                        vec_b = embeddings_dict.get(id_b, [])
                        proc_a = procurement_dict.get(id_a, {})
                        proc_b = procurement_dict.get(id_b, {})
                        
                        scores = CompositeScorer.compute_composite(
                            vec_a=vec_a,
                            vec_b=vec_b,
                            specs_a=specs_a,
                            specs_b=specs_b,
                            proc_a=proc_a,
                            proc_b=proc_b
                        )
                        
                        # Determine cluster group identifier
                        if mat_a.clean_part_number and len(mat_a.clean_part_number) >= 4:
                            cluster_sig = f"PART_{mat_a.clean_part_number[:4]}"
                        else:
                            cluster_sig = f"{mat_a.item_noun or 'GEN'}_{mat_a.nominal_size or 'NOSIZE'}_{mat_a.pressure_class or mat_a.schedule or 'NOPRESS'}"
                            
                        if cluster_sig not in clusters_map:
                            clusters_map[cluster_sig] = f"cluster_{uuid.uuid4().hex[:8]}"
                        cluster_id = clusters_map[cluster_sig]

                        # If vetoed, flag candidate and adjust tier
                        candidate = MatchCandidate(
                            job_id=job.id,
                            material_a_id=id_a,
                            material_b_id=id_b,
                            semantic_score=scores["semantic_score"],
                            attribute_score=scores["attribute_score"],
                            procurement_score=scores["procurement_score"],
                            composite_score=0.0 if is_vetoed and suggested_route == "REJECT" else scores["composite_score"],
                            safety_veto=is_vetoed,
                            veto_reason=veto_reason,
                            confidence_tier="LOW" if is_vetoed else scores["confidence_tier"],
                            cluster_group_id=cluster_id
                        )
                        db.add(candidate)
                        db.flush()
                        
                        # Add to Review Queue if score is Medium/High or if safety veto requires human sign-off
                        if scores["composite_score"] >= settings.THRESHOLD_MEDIUM or is_vetoed:
                            # Check if review entry already exists for this cluster
                            existing_review = db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == cluster_id).first()
                            if not existing_review:
                                review_entry = ReviewQueue(
                                    candidate_id=candidate.id,
                                    cluster_group_id=cluster_id,
                                    category_code=mat_a.item_noun or "GENERAL",
                                    status="PENDING",
                                    confidence_tier="HIGH" if scores["composite_score"] >= settings.THRESHOLD_HIGH and not is_vetoed else "MEDIUM"
                                )
                                db.add(review_entry)
                        
                        candidates_created += 1

            job.status = "COMPLETED"
            job.total_pairs_evaluated = total_pairs
            job.candidates_found = candidates_created
            db.commit()
            return {"status": "COMPLETED", "candidates_found": candidates_created, "pairs_evaluated": total_pairs}
            
        except Exception as e:
            db.rollback()
            job.status = "FAILED"
            db.commit()
            raise e
