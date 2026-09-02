from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.core.database import get_db, get_sync_db
from app.core.security import get_current_user, TokenData
from app.models.models import (
    ReviewQueue, MatchCandidate, Material, CPSE, ProcurementHistory,
    GoldenRecord, CNMCCode, Crosswalk, AuditLog
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
    db: Session = Depends(get_db)
):
    query = select(ReviewQueue)
    if status_filter:
        query = query.filter(ReviewQueue.status == status_filter.upper())
    if confidence_tier:
        query = query.filter(ReviewQueue.confidence_tier == confidence_tier.upper())
        
    query = query.order_by(ReviewQueue.id.desc())
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
            c0 = candidates[0]
            comp_score = c0.composite_score
            sem_score = c0.semantic_score
            attr_score = c0.attribute_score
            proc_score = c0.procurement_score
            safety_veto = c0.safety_veto
            veto_reason = c0.veto_reason
            
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

    # Determine aggregated scores
    c0 = candidates[0] if candidates else None
    scores = ScoreBreakdown(
        semantic_score=c0.semantic_score if c0 else 0.0,
        attribute_score=c0.attribute_score if c0 else 0.0,
        procurement_score=c0.procurement_score if c0 else 0.0,
        composite_score=c0.composite_score if c0 else 0.0,
        safety_veto=c0.safety_veto if c0 else False,
        veto_reason=c0.veto_reason if c0 else None,
        confidence_tier=c0.confidence_tier if c0 else "LOW"
    )

    # Synthesize proposed ISO 8000 description
    iso_synth = GoldenRecordService.synthesize_iso8000_description(materials)

    review_res = await db.execute(select(ReviewQueue).filter(ReviewQueue.cluster_group_id == cluster_group_id))
    review = review_res.scalars().first()

    return ClusterCardResponse(
        cluster_group_id=cluster_group_id,
        category_code=review.category_code if review else "VALVES",
        category_name="Refinery Flow Control & Mechanical",
        confidence_tier=review.confidence_tier if review else "HIGH",
        composite_score=scores.composite_score,
        scores=scores,
        status=review.status if review else "PENDING",
        materials=cluster_mats,
        proposed_golden_record=iso_synth["standardized_description"],
        reviewer_notes=review.reviewer_notes if review else None,
        decision_type=review.decision_type if review else None
    )

@router.post("/action")
async def execute_review_action(
    action: ReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    sync_db = next(get_sync_db())
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
        
        if action.selected_material_ids:
            materials = [m for m in materials if m.id in action.selected_material_ids]

        cnmc_code_str = None
        if action.decision_type in ["IDENTICAL", "SUBSTITUTE"]:
            # 1. Synthesize or take custom Golden Record
            synth = GoldenRecordService.synthesize_iso8000_description(materials)
            final_desc = action.custom_golden_description or synth["standardized_description"]
            
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
                canonical_attributes=synth["canonical_attributes"]
            )
            sync_db.add(golden)
            sync_db.flush()

            # 2. Mint single-authority CNMC Code
            cnmc_code_str = CNMCMinter.mint_next_cnmc(sync_db, golden.id)
            cnmc_obj = sync_db.query(CNMCCode).filter(CNMCCode.code == cnmc_code_str).first()

            # 3. Create N:1 Crosswalk links
            mapping_type = "IDENTICAL" if action.decision_type == "IDENTICAL" else "SUBSTITUTE"
            CrosswalkService.register_mappings(sync_db, cnmc_obj.id, materials, mapping_type=mapping_type)

            review.status = "APPROVED"
            review.decision_type = action.decision_type
            review.reviewer_notes = action.reviewer_notes
            
            # Log Audit Event
            AuditService.log_action(
                sync_db,
                action="CNMC_MINTED_AND_CROSSWALK_REGISTERED",
                entity_type="CNMC_CODE",
                entity_id=cnmc_code_str,
                evidence={
                    "cluster_group_id": action.cluster_group_id,
                    "materials_count": len(materials),
                    "golden_record": final_desc
                }
            )

        elif action.decision_type == "REJECT":
            review.status = "REJECTED"
            review.decision_type = "REJECTED"
            review.reviewer_notes = action.reviewer_notes
            
        elif action.decision_type == "SPLIT":
            review.status = "SPLIT"
            review.decision_type = "SPLIT"
            review.reviewer_notes = action.reviewer_notes

        sync_db.commit()
        return {
            "status": "SUCCESS",
            "cluster_group_id": action.cluster_group_id,
            "decision": action.decision_type,
            "minted_cnmc": cnmc_code_str if action.decision_type in ["IDENTICAL", "SUBSTITUTE"] else None
        }
    finally:
        sync_db.close()
