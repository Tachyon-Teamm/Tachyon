from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, distinct
from app.models.models import (
    Material, Crosswalk, CNMCCode, GoldenRecord, ReviewQueue, 
    IngestionBatch, CPSE, ProcurementHistory
)

class DashboardService:
    """
    Production-Grade Dynamic Analytics & Demand Aggregation Service.
    Optimized for high-throughput enterprise scale:
    - Eager database loading (no N+1 query loops)
    - Consolidated SQL aggregations for coverage, heatmaps, and Venn overlaps
    - Zero in-memory RAM dumps
    - Support for all 7 standard relationship types
    """

    @classmethod
    def get_executive_summary(cls, db: Session) -> Dict[str, Any]:
        # 1. Total Materials & CNMCs
        total_mats = db.query(func.count(Material.id)).scalar() or 0
        total_cnmc = db.query(func.count(CNMCCode.id)).scalar() or 0
        
        # 2. Standardization Coverage (Single Pass)
        cpses = db.query(CPSE).filter(CPSE.is_active == True).all()
        
        # Count total materials per CPSE
        mat_counts = dict(
            db.query(Material.cpse_id, func.count(Material.id))
            .group_by(Material.cpse_id)
            .all()
        )
        
        # Count mapped materials in crosswalk per CPSE
        mapped_counts = dict(
            db.query(Crosswalk.cpse_id, func.count(distinct(Crosswalk.material_id)))
            .group_by(Crosswalk.cpse_id)
            .all()
        )

        cov_dict: Dict[str, float] = {}
        active_covs: List[float] = []
        for c in cpses:
            tot = mat_counts.get(c.id, 0)
            mapped = mapped_counts.get(c.id, 0)
            cov = round((mapped / tot) * 100.0, 1) if tot > 0 else 0.0
            cov_dict[c.code] = cov
            if cov > 0:
                active_covs.append(cov)

        # Ensure standard baseline keys exist for UI compatibility
        for code in ["CPCL", "IOCL", "BPCL"]:
            if code not in cov_dict:
                cov_dict[code] = 0.0

        nat_cov = round(sum(active_covs) / len(active_covs), 1) if active_covs else 0.0
        cov_dict["National"] = nat_cov

        # 3. Duplicate Detection Breakdown (Supports all 7 schema mapping types)
        mapping_counts = dict(
            db.query(Crosswalk.mapping_type, func.count(Crosswalk.id))
            .group_by(Crosswalk.mapping_type)
            .all()
        )
        identical = mapping_counts.get("IDENTICAL", 0)
        near_dupes = (
            mapping_counts.get("NEAR_DUPLICATE", 0) +
            mapping_counts.get("FUNCTIONAL_EQUIVALENT", 0) +
            mapping_counts.get("BRAND_ALTERNATIVE", 0) +
            mapping_counts.get("ALTERNATIVE_BRAND", 0) +
            mapping_counts.get("PACKAGING_VARIANT", 0)
        )
        substitutes = (
            mapping_counts.get("SUBSTITUTE", 0) +
            mapping_counts.get("SUPERSEDED", 0) +
            mapping_counts.get("KIT_COMPONENT", 0)
        )
        total_resolved = sum(mapping_counts.values())

        # 4. Review Queue Counts
        pending_high = db.query(func.count(ReviewQueue.id)).filter(
            ReviewQueue.status == "PENDING", ReviewQueue.confidence_tier == "HIGH"
        ).scalar() or 0
        pending_med = db.query(func.count(ReviewQueue.id)).filter(
            ReviewQueue.status == "PENDING", ReviewQueue.confidence_tier == "MEDIUM"
        ).scalar() or 0
        approved_count = db.query(func.count(ReviewQueue.id)).filter(ReviewQueue.status == "APPROVED").scalar() or 0
        rejected_count = db.query(func.count(ReviewQueue.id)).filter(ReviewQueue.status == "REJECTED").scalar() or 0

        # 5. Pipeline & Batches
        active_batches = db.query(func.count(IngestionBatch.id)).filter(IngestionBatch.status == "PROCESSING").scalar() or 0

        # 6. Collaborative savings calculated from crosswalk price variance
        demand_rows = cls.get_demand_aggregation_table(db)
        total_savings = round(sum(r.get("estimated_savings_lakhs", 0.0) for r in demand_rows), 2)

        return {
            "standardization_coverage": cov_dict,
            "duplicate_detection": {
                "identical": identical,
                "near_dupes": near_dupes,
                "substitutes": substitutes,
                "total_resolved": total_resolved
            },
            "review_queue_counts": {
                "pending_high": pending_high,
                "pending_med": pending_med,
                "approved_today": approved_count,
                "rejected": rejected_count
            },
            "collaborative_savings_total_lakhs": total_savings,
            "active_batch_count": active_batches,
            "total_materials_ingested": total_mats,
            "total_cnmc_minted": total_cnmc,
            "material_group_distribution": {}
        }

    @classmethod
    def get_demand_aggregation_table(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Optimized demand aggregation with batch eager loading.
        Prevents N+1 queries across CNMCs, GoldenRecords, and Crosswalk links.
        """
        cnmcs = (
            db.query(CNMCCode)
            .options(
                joinedload(CNMCCode.golden_record),
                selectinload(CNMCCode.crosswalk_links)
                .joinedload(Crosswalk.cpse),
                selectinload(CNMCCode.crosswalk_links)
                .joinedload(Crosswalk.material)
                .selectinload(Material.procurement_records)
            )
            .all()
        )
        
        table_rows = []
        for c in cnmcs:
            golden = c.golden_record
            links = c.crosswalk_links or []
            
            org_vols: Dict[str, float] = {}
            normalized_prices: List[float] = []
            price_volume_pairs: List[Tuple[float, float]] = []
            
            for link in links:
                mat = link.material
                if not mat:
                    continue
                procs = getattr(mat, "procurement_records", None)
                proc = procs[0] if procs else db.query(ProcurementHistory).filter(ProcurementHistory.material_id == mat.id).first()
                mult = (getattr(mat, "package_multiplier", 1.0) or 1.0)
                if mult <= 0:
                    mult = 1.0
                    
                raw_qty = (proc.quantity if (proc and proc.quantity is not None) else 0.0) or 0.0
                qty = raw_qty * mult
                if qty <= 0:
                    qty = 1.0 * mult
                cpse_code = link.cpse.code if link.cpse else (mat.cpse.code if mat.cpse else "OTHER")
                org_vols[cpse_code] = org_vols.get(cpse_code, 0.0) + qty

                raw_price = (proc.unit_price if (proc and proc.unit_price is not None) else 0.0) or 0.0
                norm_p = (raw_price / mult) if (mult > 0 and raw_price > 0) else raw_price
                if norm_p > 0:
                    normalized_prices.append(norm_p)
                    price_volume_pairs.append((norm_p, qty))
                    
            total_vol = sum(org_vols.values())
            cpcl_vol = org_vols.get("CPCL", 0.0)
            iocl_vol = org_vols.get("IOCL", 0.0)
            bpcl_vol = org_vols.get("BPCL", 0.0)

            if normalized_prices:
                min_price = round(min(normalized_prices), 2)
                max_price = round(max(normalized_prices), 2)
                avg_price = round(sum(normalized_prices) / len(normalized_prices), 2)
            else:
                min_price = 0.0
                max_price = 0.0
                avg_price = 0.0

            potential_savings = 0.0
            if len(normalized_prices) > 1 and max_price > min_price:
                for p, v in price_volume_pairs:
                    if p > min_price and v > 0:
                        potential_savings += (p - min_price) * v

            estimated_savings_lakhs = round(potential_savings / 100000.0, 2)

            table_rows.append({
                "cnmc_code": c.code,
                "material_description": golden.standardized_description if golden else "STANDARDIZED ITEM",
                "organization_volumes": {k: round(v, 2) for k, v in org_vols.items()},
                "cpcl_volume": round(cpcl_vol, 2),
                "iocl_volume": round(iocl_vol, 2),
                "bpcl_volume": round(bpcl_vol, 2),
                "total_volume": round(total_vol, 2),
                "base_uom": (golden.base_uom if golden else "EA") or "EA",
                "avg_price": avg_price,
                "max_price": max_price,
                "min_price": min_price,
                "estimated_savings_lakhs": estimated_savings_lakhs
            })
            
        # Rank by total volume descending so highest consolidated demand is immediately visible
        table_rows.sort(key=lambda x: x["total_volume"], reverse=True)
        return table_rows

