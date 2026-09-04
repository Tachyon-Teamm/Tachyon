from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.core.database import get_db, get_sync_db, get_sync_session
from app.core.security import get_current_user, TokenData
from app.models.models import (
    ReviewQueue, MatchCandidate, Material, CPSE, ProcurementHistory,
    GoldenRecord, CNMCCode, Crosswalk, AuditLog, ReviewFeedback, TaxonomyCategory
)
from app.schemas.schemas import (
    ClusterCardResponse, ClusterMaterialItem, ScoreBreakdown,
    ReviewActionRequest, MaterialResponse, ExtractedSpecs
)
from app.services.governance.golden_record_service import GoldenRecordService
from app.services.governance.cnmc_minter import CNMCMinter
from app.services.governance.crosswalk_service import CrosswalkService
from app.services.governance.audit_service import AuditService

router = APIRouter(prefix="/review", tags=["Review Queue & Governance"])

@router.get("/queue")
async def get_review_queue(
    status_filter: Optional[str] = "PENDING",
    confidence_tier: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    query = select(ReviewQueue)
    if status_filter:
        query = query.filter(ReviewQueue.status == status_filter.upper())
    if confidence_tier:
        query = query.filter(ReviewQueue.confidence_tier == confidence_tier.upper())
        
    query = query.order_by(ReviewQueue.id.desc())
    if limit is not None and limit > 0:
        query = query.limit(limit)
    if offset is not None and offset > 0:
        query = query.offset(offset)
        
    res = await db.execute(query)
    items = res.scalars().all()
    
    out = []
    for item in items:
        # Get candidates in this cluster
        cand_res = await db.execute(select(MatchCandidate).filter(MatchCandidate.cluster_group_id == item.cluster_group_id))
        candidates = cand_res.scalars().all()
        
        comp_score = 0.0
        sem_score = 0.0
        attr_score = 0.0
        proc_score = 0.0
        safety_veto = False
        veto_reason = None
        
        if candidates:
            safety_veto = any(c.safety_veto for c in candidates)
            veto_reason = next((c.veto_reason for c in candidates if c.safety_veto and c.veto_reason), None)
            comp_score = round(sum(c.composite_score for c in candidates) / len(candidates), 4)
            sem_score = round(sum(c.semantic_score for c in candidates) / len(candidates), 4)
            attr_score = round(sum(c.attribute_score for c in candidates) / len(candidates), 4)
            proc_score = round(sum(c.procurement_score for c in candidates) / len(candidates), 4)
            
        out.append({
            "id": item.id,
            "cluster_group_id": item.cluster_group_id,
            "category_code": item.category_code or "GENERAL",
            "status": item.status,
            "confidence_tier": item.confidence_tier,
            "composite_score": comp_score,
            "safety_veto": safety_veto,
            "veto_reason": veto_reason,
            "created_at": item.created_at
        })
    return out

@router.get("/cluster/{cluster_group_id}", response_model=ClusterCardResponse)
async def get_cluster_details(cluster_group_id: str, db: Session = Depends(get_db)):
    # Find all candidates belonging to this cluster
    cand_res = await db.execute(select(MatchCandidate).filter(MatchCandidate.cluster_group_id == cluster_group_id))
    candidates = cand_res.scalars().all()
    
    # Collect all material IDs in this cluster
    mat_ids = set()
    for c in candidates:
        mat_ids.add(c.material_a_id)
        mat_ids.add(c.material_b_id)
        
    if not mat_ids:
        raise HTTPException(status_code=404, detail="Cluster not found")

    mats_res = await db.execute(select(Material).filter(Material.id.in_(list(mat_ids))))
    materials = mats_res.scalars().all()

    cluster_mats: List[ClusterMaterialItem] = []
    for m in materials:
        cpse_res = await db.execute(select(CPSE).filter(CPSE.id == m.cpse_id))
        cpse = cpse_res.scalars().first()
        proc_res = await db.execute(select(ProcurementHistory).filter(ProcurementHistory.material_id == m.id))
        proc = proc_res.scalars().first()

        specs_dict = m.extracted_attributes or {}
        specs_obj = ExtractedSpecs(
            item_noun=m.item_noun,
            nominal_size=m.nominal_size,
            pressure_class=m.pressure_class,
            moc=m.moc,
            schedule=m.schedule,
            end_connection=m.end_connection,
            standard_spec=m.standard_spec,
            part_number=m.part_number,
            clean_part_number=m.clean_part_number,
            clearance_suffix=m.clearance_suffix,
            is_kit_or_assembly=m.is_kit_or_assembly,
            package_multiplier=m.package_multiplier,
            base_uom=m.base_uom or "EA",
            extra_attributes=specs_dict
        )

        mat_resp = MaterialResponse(
            id=m.id,
            cpse_id=m.cpse_id,
            cpse_code=cpse.code if cpse else "UNK",
            material_code=m.material_code,
            short_description=m.short_description,
            uom=m.uom,
            base_uom=m.base_uom or "EA",
            package_multiplier=m.package_multiplier,
            item_noun=m.item_noun,
            nominal_size=m.nominal_size,
            pressure_class=m.pressure_class,
            moc=m.moc,
            schedule=m.schedule,
            end_connection=m.end_connection,
            standard_spec=m.standard_spec,
            clean_part_number=m.clean_part_number,
            clearance_suffix=m.clearance_suffix,
            is_kit_or_assembly=m.is_kit_or_assembly,
            category_code=m.category_code,
            category_confidence=m.category_confidence,
            predicted_category_name=m.predicted_category_name,
            status=m.status,
            last_po_price=proc.unit_price if proc else None,
            vendor_name=proc.vendor_name if proc else None,
            created_at=m.created_at
        )

        cluster_mats.append(ClusterMaterialItem(
            material=mat_resp,
            vendor_name=proc.vendor_name if proc else None,
            last_po_price=proc.unit_price if proc else None,
            po_quantity=proc.quantity if proc else 1.0,
            specs=specs_obj
        ))

    # Determine aggregated scores across all candidates in cluster
    if candidates:
        has_veto = any(c.safety_veto for c in candidates)
        v_reason = next((c.veto_reason for c in candidates if c.safety_veto and c.veto_reason), None)
        mean_comp = round(sum(c.composite_score for c in candidates) / len(candidates), 4)
        mean_sem = round(sum(c.semantic_score for c in candidates) / len(candidates), 4)
        mean_attr = round(sum(c.attribute_score for c in candidates) / len(candidates), 4)
        mean_proc = round(sum(c.procurement_score for c in candidates) / len(candidates), 4)
        tier = "LOW" if has_veto else ("HIGH" if mean_comp >= 0.90 else "MEDIUM")
        scores = ScoreBreakdown(
            semantic_score=mean_sem,
            attribute_score=mean_attr,
            procurement_score=mean_proc,
            composite_score=mean_comp,
            safety_veto=has_veto,
            veto_reason=v_reason,
            confidence_tier=tier
        )
    else:
        scores = ScoreBreakdown(
            semantic_score=0.0,
            attribute_score=0.0,
            procurement_score=0.0,
            composite_score=0.0,
            safety_veto=False,
            veto_reason=None,
            confidence_tier="LOW"
        )

    # Synthesize proposed ISO 8000 description
    iso_synth = GoldenRecordService.synthesize_iso8000_description(materials)

    review_res = await db.execute(select(ReviewQueue).filter(ReviewQueue.cluster_group_id == cluster_group_id))
    review = review_res.scalars().first()

    cat_name = "Industrial Materials"
    if review and review.category_code:
        cat_res = await db.execute(select(TaxonomyCategory).filter(TaxonomyCategory.unspsc_code == review.category_code))
        cat_obj = cat_res.scalars().first()
        if cat_obj:
            cat_name = cat_obj.name
        elif materials and materials[0].item_noun:
            cat_name = f"{materials[0].item_noun} Category"
        else:
            cat_name = f"{review.category_code} Category"
    elif materials and materials[0].item_noun:
        cat_name = f"{materials[0].item_noun} Category"

    return ClusterCardResponse(
        cluster_group_id=cluster_group_id,
        category_code=review.category_code if review else "VALVES",
        category_name=cat_name,
        confidence_tier=review.confidence_tier if review else "HIGH",
        composite_score=scores.composite_score,
        scores=scores,
        status=review.status if review else "PENDING",
        materials=cluster_mats,
        proposed_golden_record=iso_synth["standardized_description"],
        reviewer_notes=review.reviewer_notes if review else None,
        decision_type=review.decision_type if review else None
    )

APPROVED_RELATIONSHIPS = {
    "IDENTICAL", "FUNCTIONAL_EQUIVALENT", "BRAND_ALTERNATIVE", 
    "KIT_COMPONENT", "PACKAGING_VARIANT", "SUPERSEDED", "SUBSTITUTE"
}

@router.post("/action")
async def execute_review_action(
    action: ReviewActionRequest,
    current_user: TokenData = Depends(get_current_user)
):
    sync_db = get_sync_session()
    try:
        review = sync_db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == action.cluster_group_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review cluster not found")

        cand_res = sync_db.query(MatchCandidate).filter(MatchCandidate.cluster_group_id == action.cluster_group_id).all()
        mat_ids = set()
        for c in cand_res:
            mat_ids.add(c.material_a_id)
            mat_ids.add(c.material_b_id)
            
        materials = sync_db.query(Material).filter(Material.id.in_(list(mat_ids))).all()
        
        if action.selected_material_ids is not None:
            materials = [m for m in materials if m.id in action.selected_material_ids]

        cnmc_code_str = None
        decision_upper = action.decision_type.upper()
        reviewer_user_id = getattr(current_user, "user_id", None) or getattr(current_user, "cpse_id", None) or 1

        # Idempotency check: if cluster is already approved, return existing minted CNMC
        if review.status == "APPROVED" and decision_upper in APPROVED_RELATIONSHIPS:
            existing_golden = sync_db.query(GoldenRecord).filter(GoldenRecord.review_queue_id == review.id).first()
            existing_cnmc = sync_db.query(CNMCCode).filter(CNMCCode.golden_record_id == existing_golden.id).first() if existing_golden else None
            return {
                "status": "SUCCESS",
                "cluster_group_id": action.cluster_group_id,
                "decision": review.decision_type or decision_upper,
                "minted_cnmc": existing_cnmc.code if existing_cnmc else None,
                "message": "Cluster already approved"
            }

        # Guard against empty material selection
        if decision_upper in APPROVED_RELATIONSHIPS and not materials:
            raise HTTPException(status_code=400, detail="Cannot approve cluster with 0 selected materials")

        # Active Learning Telemetry Store: Record decision for contrastive fine-tuning
        for c in cand_res:
            feedback_entry = ReviewFeedback(
                candidate_id=c.id,
                material_a_id=c.material_a_id,
                material_b_id=c.material_b_id,
                feature_vector={
                    "semantic_score": c.semantic_score,
                    "attribute_score": c.attribute_score,
                    "procurement_score": c.procurement_score,
                    "composite_score": c.composite_score
                },
                human_decision=action.decision_type,
                reviewer_notes=action.reviewer_notes,
                reviewer_id=reviewer_user_id
            )
            sync_db.add(feedback_entry)

        if decision_upper in APPROVED_RELATIONSHIPS:
            # 1. Synthesize or take custom Golden Record
            synth = GoldenRecordService.synthesize_iso8000_description(materials)
            final_desc = (action.custom_golden_description or "").strip() or synth["standardized_description"]
            if len(final_desc) > 500:
                final_desc = final_desc[:497] + "..."
            
            golden = GoldenRecord(
                review_queue_id=review.id,
                standardized_description=final_desc,
                item_noun=synth["item_noun"],
                modifier=synth["modifier"],
                nominal_size=synth["nominal_size"],
                pressure_class=synth["pressure_class"],
                moc=synth["moc"],
                schedule=synth["schedule"],
                end_connection=synth["end_connection"],
                standard_spec=synth["standard_spec"],
                base_uom=synth["base_uom"],
                technical_attributes=synth.get("technical_attributes", {}),
                canonical_attributes=synth.get("canonical_attributes", {})
            )
            sync_db.add(golden)
            sync_db.flush()

            # 2. Mint single-authority CNMC Code
            cnmc_code_str = CNMCMinter.mint_next_cnmc(sync_db, golden.id)
            cnmc_obj = sync_db.query(CNMCCode).filter(CNMCCode.code == cnmc_code_str).first()

            # 3. Create N:1 Crosswalk links with exact relationship taxonomy
            CrosswalkService.register_mappings(sync_db, cnmc_obj.id, materials, mapping_type=decision_upper)

            review.status = "APPROVED"
            review.decision_type = decision_upper
            review.reviewer_notes = action.reviewer_notes
            review.reviewer_id = reviewer_user_id
            review.reviewed_at = datetime.now(timezone.utc)
            
            # Log Audit Event
            AuditService.log_action(
                sync_db,
                action="CNMC_MINTED_AND_CROSSWALK_REGISTERED",
                entity_type="CNMC_CODE",
                entity_id=cnmc_code_str,
                user_id=reviewer_user_id,
                evidence={
                    "cluster_group_id": action.cluster_group_id,
                    "materials_count": len(materials),
                    "mapping_type": decision_upper,
                    "golden_record": final_desc
                }
            )

        elif decision_upper in ("REJECT", "INCOMPATIBLE"):
            review.status = "REJECTED"
            review.decision_type = decision_upper
            review.reviewer_notes = action.reviewer_notes
            review.reviewer_id = reviewer_user_id
            review.reviewed_at = datetime.now(timezone.utc)
            
            AuditService.log_action(
                sync_db,
                action="REVIEW_CLUSTER_REJECTED",
                entity_type="REVIEW_QUEUE",
                entity_id=action.cluster_group_id,
                user_id=reviewer_user_id,
                evidence={
                    "cluster_group_id": action.cluster_group_id,
                    "decision": decision_upper,
                    "reviewer_notes": action.reviewer_notes,
                    "materials_count": len(materials)
                }
            )
            
        elif decision_upper == "SPLIT":
            review.status = "SPLIT"
            review.decision_type = "SPLIT"
            review.reviewer_notes = action.reviewer_notes
            review.reviewer_id = reviewer_user_id
            review.reviewed_at = datetime.now(timezone.utc)

            AuditService.log_action(
                sync_db,
                action="REVIEW_CLUSTER_SPLIT",
                entity_type="REVIEW_QUEUE",
                entity_id=action.cluster_group_id,
                user_id=reviewer_user_id,
                evidence={
                    "cluster_group_id": action.cluster_group_id,
                    "decision": "SPLIT",
                    "reviewer_notes": action.reviewer_notes,
                    "selected_material_ids": action.selected_material_ids,
                    "materials_count": len(materials)
                }
            )

        sync_db.commit()
        return {
            "status": "SUCCESS",
            "cluster_group_id": action.cluster_group_id,
            "decision": decision_upper,
            "minted_cnmc": cnmc_code_str if decision_upper in APPROVED_RELATIONSHIPS else None
        }
    finally:
        sync_db.close()

class BulkApproveRequest(BaseModel):
    cluster_group_ids: List[str]
    reviewer_notes: Optional[str] = "Bulk approved high-confidence matches"

@router.post("/bulk-approve")
def bulk_approve_clusters(
    payload: Union[List[str], BulkApproveRequest] = Body(...),
    reviewer_notes: Optional[str] = "Bulk approved high-confidence matches",
    current_user: TokenData = Depends(get_current_user)
):
    """
    Fast-Track Bulk Approval for Tier 1 High Confidence (>=95%) Clusters.
    Supports both raw JSON array (['cluster_1']) and object payloads ({'cluster_group_ids': ['cluster_1']}).
    """
    if isinstance(payload, list):
        cluster_group_ids = payload
        effective_notes = reviewer_notes or "Bulk approved high-confidence matches"
    else:
        cluster_group_ids = payload.cluster_group_ids
        effective_notes = payload.reviewer_notes or reviewer_notes or "Bulk approved high-confidence matches"

    sync_db = get_sync_session()
    approved_clusters = []
    try:
        for cid in cluster_group_ids:
            review = sync_db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == cid).first()
            if not review or review.status == "APPROVED":
                continue

            # Fetch cluster candidates and materials
            cands = sync_db.query(MatchCandidate).filter(MatchCandidate.cluster_group_id == cid).all()
            if not cands:
                continue

            # HARD DETERMINISTIC SAFETY INVARIANT CHECK:
            # Strictly veto and skip any cluster containing safety invariant violations
            if any(c.safety_veto for c in cands):
                continue

            mat_ids = set()
            for c in cands:
                mat_ids.add(c.material_a_id)
                mat_ids.add(c.material_b_id)

            if not mat_ids:
                continue

            mats = sync_db.query(Material).filter(Material.id.in_(list(mat_ids))).all()
            if not mats:
                continue

            synth = GoldenRecordService.synthesize_iso8000_description(mats)
            golden = GoldenRecord(
                review_queue_id=review.id,
                standardized_description=synth["standardized_description"],
                item_noun=synth["item_noun"],
                modifier=synth["modifier"],
                nominal_size=synth["nominal_size"],
                pressure_class=synth["pressure_class"],
                moc=synth["moc"],
                schedule=synth["schedule"],
                end_connection=synth["end_connection"],
                standard_spec=synth["standard_spec"],
                base_uom=synth["base_uom"],
                technical_attributes=synth.get("technical_attributes", {}),
                canonical_attributes=synth.get("canonical_attributes", {})
            )
            sync_db.add(golden)
            sync_db.flush()

            cnmc_code = CNMCMinter.mint_next_cnmc(sync_db, golden.id)
            cnmc_obj = sync_db.query(CNMCCode).filter(CNMCCode.code == cnmc_code).first()

            reviewer_user_id = getattr(current_user, "user_id", None) or getattr(current_user, "cpse_id", None) or 1
            CrosswalkService.register_mappings(sync_db, cnmc_obj.id, mats, mapping_type="IDENTICAL")
            review.status = "APPROVED"
            review.decision_type = "IDENTICAL"
            review.reviewer_notes = effective_notes
            review.reviewer_id = reviewer_user_id
            review.reviewed_at = datetime.now(timezone.utc)

            # Record ReviewFeedback for active learning telemetry
            for c in cands:
                sync_db.add(ReviewFeedback(
                    candidate_id=c.id,
                    material_a_id=c.material_a_id,
                    material_b_id=c.material_b_id,
                    feature_vector={
                        "semantic_score": c.semantic_score,
                        "attribute_score": c.attribute_score,
                        "procurement_score": c.procurement_score,
                        "composite_score": c.composite_score
                    },
                    human_decision="IDENTICAL",
                    reviewer_notes=effective_notes,
                    reviewer_id=reviewer_user_id
                ))

            AuditService.log_action(
                sync_db,
                action="BULK_REVIEW_APPROVED",
                entity_type="CNMC_CODE",
                entity_id=cnmc_code,
                user_id=reviewer_user_id,
                evidence={"cluster_group_id": cid, "material_count": len(mats)}
            )
            approved_clusters.append({"cluster_group_id": cid, "cnmc": cnmc_code})

        sync_db.commit()
        return {
            "status": "SUCCESS",
            "approved_count": len(approved_clusters),
            "approved_clusters": approved_clusters
        }
    finally:
        sync_db.close()

@router.post("/dispute")
def dispute_cluster(
    cluster_group_id: str,
    dispute_reason: str,
    dissenting_cpse_code: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Multi-CPSE Dispute & Arbitration Endpoint:
    Transitions cluster to DISPUTED status with technical reasoning for Lead Arbiter review.
    """
    sync_db = get_sync_session()
    try:
        review = sync_db.query(ReviewQueue).filter(ReviewQueue.cluster_group_id == cluster_group_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review cluster not found")

        reviewer_user_id = getattr(current_user, "user_id", None) or getattr(current_user, "cpse_id", None) or 1
        review.status = "DISPUTED"
        review.reviewer_notes = f"[DISPUTED by {dissenting_cpse_code or 'CPSE Steward'}]: {dispute_reason}"
        review.reviewer_id = reviewer_user_id
        review.reviewed_at = datetime.now(timezone.utc)

        AuditService.log_action(
            sync_db,
            action="MULTI_CPSE_DISPUTE_FILED",
            entity_type="REVIEW_QUEUE",
            entity_id=cluster_group_id,
            user_id=reviewer_user_id,
            evidence={
                "cluster_group_id": cluster_group_id,
                "dispute_reason": dispute_reason,
                "dissenting_cpse": dissenting_cpse_code
            }
        )
        sync_db.commit()
        return {
            "status": "SUCCESS",
            "cluster_group_id": cluster_group_id,
            "lifecycle_state": "DISPUTED",
            "assigned_to": "NATIONAL_DATA_STEWARD"
        }
    finally:
        sync_db.close()

@router.get("/feedback/export")
def export_feedback_dataset():
    """
    Active Learning Feedback Dataset Exporter:
    Exports reviewer decisions (Positive & Negative pairs) for model benchmarking and fine-tuning.
    """
    sync_db = get_sync_session()
    try:
        feedbacks = sync_db.query(ReviewFeedback).order_by(ReviewFeedback.created_at.desc()).all()
        dataset = []
        if feedbacks:
            for fb in feedbacks:
                feat = fb.feature_vector or {}
                dataset.append({
                    "feedback_id": fb.id,
                    "candidate_id": fb.candidate_id,
                    "material_a_id": fb.material_a_id,
                    "material_b_id": fb.material_b_id,
                    "composite_score": feat.get("composite_score", 0.0),
                    "semantic_score": feat.get("semantic_score", 0.0),
                    "attribute_score": feat.get("attribute_score", 0.0),
                    "procurement_score": feat.get("procurement_score", 0.0),
                    "human_decision": fb.human_decision,
                    "is_positive_match": fb.human_decision in APPROVED_RELATIONSHIPS,
                    "reviewer_notes": fb.reviewer_notes,
                    "created_at": fb.created_at.isoformat() if fb.created_at else None
                })
        else:
            reviews = sync_db.query(ReviewQueue).filter(ReviewQueue.status.in_(["APPROVED", "REJECTED", "DISPUTED"])).all()
            for r in reviews:
                cands = sync_db.query(MatchCandidate).filter(MatchCandidate.cluster_group_id == r.cluster_group_id).all()
                for c in cands:
                    dataset.append({
                        "cluster_group_id": r.cluster_group_id,
                        "material_a_id": c.material_a_id,
                        "material_b_id": c.material_b_id,
                        "composite_score": c.composite_score,
                        "semantic_score": c.semantic_score,
                        "attribute_score": c.attribute_score,
                        "procurement_score": c.procurement_score,
                        "safety_veto": c.safety_veto,
                        "human_decision": r.decision_type or r.status,
                        "is_positive_match": r.status == "APPROVED"
                    })
        return {
            "total_samples": len(dataset),
            "samples": dataset
        }
    finally:
        sync_db.close()

class PromoteSingletonsRequest(BaseModel):
    cpse_id: Optional[int] = None

@router.post("/promote-singletons")
def promote_singletons_endpoint(
    payload: Optional[PromoteSingletonsRequest] = Body(None),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Singleton Canonical Promotion endpoint:
    Mints authoritative CNMC codes and crosswalk mappings for all un-clustered materials.
    """
    sync_db = get_sync_session()
    try:
        target_cpse_id = payload.cpse_id if payload else None
        res = GoldenRecordService.promote_singleton_materials(sync_db, cpse_id=target_cpse_id)
        return res
    finally:
        sync_db.close()
