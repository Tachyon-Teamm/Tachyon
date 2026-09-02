from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from app.models.models import (
    Material, Crosswalk, CNMCCode, GoldenRecord, ReviewQueue, 
    MatchCandidate, IngestionBatch, CPSE, ProcurementHistory
)

class DashboardService:
    """
    100% Dynamic Analytics & Demand Aggregation Service.
    Zero hardcoded values. All metrics computed directly from database tables.
    """

    @classmethod
    def get_executive_summary(cls, db: Session) -> Dict[str, Any]:
        # 1. Total Materials Ingested
        total_mats = db.query(func.count(Material.id)).scalar() or 0
        total_cnmc = db.query(func.count(CNMCCode.id)).scalar() or 0
        
        # 2. Standardization Coverage
        cpcl = db.query(CPSE).filter(CPSE.code == "CPCL").first()
        iocl = db.query(CPSE).filter(CPSE.code == "IOCL").first()
        bpcl = db.query(CPSE).filter(CPSE.code == "BPCL").first()
        
        def get_cov(cpse_id: int) -> float:
            if not cpse_id:
                return 0.0
            tot = db.query(func.count(Material.id)).filter(Material.cpse_id == cpse_id).scalar() or 0
            if tot == 0:
                return 0.0
            mapped = db.query(func.count(distinct(Crosswalk.material_id))).filter(Crosswalk.cpse_id == cpse_id).scalar() or 0
            return round((mapped / tot) * 100.0, 1)

        cpcl_cov = get_cov(cpcl.id if cpcl else None)
        iocl_cov = get_cov(iocl.id if iocl else None)
        bpcl_cov = get_cov(bpcl.id if bpcl else None)
        
        active_cposes = [c for c in [cpcl_cov, iocl_cov, bpcl_cov] if c > 0]
        nat_cov = round(sum(active_cposes) / len(active_cposes), 1) if active_cposes else 0.0

        # 3. Duplicate Detection Breakdown
        identical = db.query(func.count(Crosswalk.id)).filter(Crosswalk.mapping_type == "IDENTICAL").scalar() or 0
        near_dupes = db.query(func.count(Crosswalk.id)).filter(Crosswalk.mapping_type == "NEAR_DUPLICATE").scalar() or 0
        substitutes = db.query(func.count(Crosswalk.id)).filter(Crosswalk.mapping_type == "SUBSTITUTE").scalar() or 0
        total_resolved = identical + near_dupes + substitutes

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

        # 6. Dynamically Calculate Total Collaborative Savings
        demand_rows = cls.get_demand_aggregation_table(db)
        total_savings = round(sum(r["estimated_savings_lakhs"] for r in demand_rows), 2)

        # 7. Material Group Taxonomy Distribution (Dynamic from DB)
        all_mats = db.query(Material.item_noun).all()
        total_with_noun = len(all_mats)
        group_counts: Dict[str, int] = {}
        if total_with_noun > 0:
            for (noun,) in all_mats:
                if not noun:
                    cat = "Other Items"
                elif "VALVE" in noun:
                    cat = "Valves & Flow Control"
                elif "PIPE" in noun or "TUBING" in noun:
                    cat = "Pipes & Tubing"
                elif "BEARING" in noun:
                    cat = "Bearings & Bushings"
                elif "GASKET" in noun or "SEAL" in noun:
                    cat = "Gaskets & Seals"
                elif "GREASE" in noun or "OIL" in noun or "LUBRICANT" in noun:
                    cat = "Lubricants & Greases"
                elif "FLANGE" in noun:
                    cat = "Flanges & Fittings"
                else:
                    cat = "Other Items"
                group_counts[cat] = group_counts.get(cat, 0) + 1
            
            mat_distribution = {
                cat: round((cnt / total_with_noun) * 100.0, 1)
                for cat, cnt in sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
            }
        else:
            mat_distribution = {
                "Valves & Flow Control": 0.0,
                "Pipes & Tubing": 0.0,
                "Bearings & Bushings": 0.0,
                "Gaskets & Seals": 0.0,
                "Lubricants & Greases": 0.0
            }

        return {
            "standardization_coverage": {
                "National": nat_cov,
                "CPCL": cpcl_cov,
                "IOCL": iocl_cov,
                "BPCL": bpcl_cov
            },
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
            "material_group_distribution": mat_distribution
        }

    @classmethod
    def get_demand_aggregation_table(cls, db: Session) -> List[Dict[str, Any]]:
        cnmcs = db.query(CNMCCode).join(GoldenRecord).all()
        table_rows = []
        
        for c in cnmcs:
            golden = c.golden_record
            links = db.query(Crosswalk).filter(Crosswalk.cnmc_id == c.id).all()
            
            cpcl_vol = 0.0
            iocl_vol = 0.0
            bpcl_vol = 0.0
            prices = []
            
            for link in links:
                mat = link.material
                proc = db.query(ProcurementHistory).filter(ProcurementHistory.material_id == mat.id).first()
                mult = (getattr(mat, "package_multiplier", 1.0) or 1.0)
                qty = (proc.quantity if (proc and proc.quantity is not None) else 0.0) * mult
                price = proc.unit_price if (proc and proc.unit_price is not None) else 0.0
                norm_price = (price / mult) if (mult > 0 and price > 0) else price
                
                if norm_price > 0:
                    prices.append(norm_price)
                    
                if mat.cpse and mat.cpse.code == "CPCL":
                    cpcl_vol += qty
                elif mat.cpse and mat.cpse.code == "IOCL":
                    iocl_vol += qty
                elif mat.cpse and mat.cpse.code == "BPCL":
                    bpcl_vol += qty
                    
            total_vol = cpcl_vol + iocl_vol + bpcl_vol
            if not prices:
                avg_p, min_p, max_p = 0.0, 0.0, 0.0
                savings_lakhs = 0.0
            else:
                avg_p = sum(prices) / len(prices)
                min_p = min(prices)
                max_p = max(prices)
                diff = max_p - min_p
                savings_lakhs = round((diff * total_vol) / 100000.0, 2)

            table_rows.append({
                "cnmc_code": c.code,
                "material_description": golden.standardized_description if golden else "STANDARDIZED ITEM",
                "cpcl_volume": cpcl_vol,
                "iocl_volume": iocl_vol,
                "bpcl_volume": bpcl_vol,
                "total_volume": total_vol,
                "base_uom": (golden.base_uom if golden else "EA") or "EA",
                "avg_price": round(avg_p, 2),
                "max_price": round(max_p, 2),
                "min_price": round(min_p, 2),
                "estimated_savings_lakhs": savings_lakhs
            })
            
        return table_rows

    @classmethod
    def get_data_quality_heatmap(cls, db: Session) -> List[Dict[str, Any]]:
        # Calculate real completeness % of critical fields across CPSEs
        def calc_field_pct(field_attr, cpse_code: str) -> float:
            cpse = db.query(CPSE).filter(CPSE.code == cpse_code).first()
            if not cpse:
                return 0.0
            tot = db.query(func.count(Material.id)).filter(Material.cpse_id == cpse.id).scalar() or 0
            if tot == 0:
                return 0.0
            non_null = db.query(func.count(Material.id)).filter(
                Material.cpse_id == cpse.id,
                field_attr.isnot(None)
            ).scalar() or 0
            return round((non_null / tot) * 100.0, 1)

        return [
            {
                "field_name": "Size / Dimensions",
                "cpcl_pct": calc_field_pct(Material.nominal_size, "CPCL"),
                "iocl_pct": calc_field_pct(Material.nominal_size, "IOCL"),
                "bpcl_pct": calc_field_pct(Material.nominal_size, "BPCL"),
            },
            {
                "field_name": "Pressure Class",
                "cpcl_pct": calc_field_pct(Material.pressure_class, "CPCL"),
                "iocl_pct": calc_field_pct(Material.pressure_class, "IOCL"),
                "bpcl_pct": calc_field_pct(Material.pressure_class, "BPCL"),
            },
            {
                "field_name": "MOC / Metallurgy",
                "cpcl_pct": calc_field_pct(Material.moc, "CPCL"),
                "iocl_pct": calc_field_pct(Material.moc, "IOCL"),
                "bpcl_pct": calc_field_pct(Material.moc, "BPCL"),
            },
            {
                "field_name": "Standard / Spec",
                "cpcl_pct": calc_field_pct(Material.standard_spec, "CPCL"),
                "iocl_pct": calc_field_pct(Material.standard_spec, "IOCL"),
                "bpcl_pct": calc_field_pct(Material.standard_spec, "BPCL"),
            }
        ]

    @classmethod
    def get_venn_overlap(cls, db: Session) -> Dict[str, int]:
        # Count overlapping materials mapped to shared CNMCs directly from database
        all_three = 0
        cpcl_iocl = 0
        iocl_bpcl = 0
        cpcl_bpcl = 0
        cpcl_only = 0
        iocl_only = 0
        bpcl_only = 0
        
        cnmcs = db.query(CNMCCode).all()
        for c in cnmcs:
            cpses_in_cnmc = db.query(CPSE.code).join(Crosswalk).filter(Crosswalk.cnmc_id == c.id).all()
            codes = {x[0] for x in cpses_in_cnmc}
            if len(codes) >= 3:
                all_three += 1
            elif "CPCL" in codes and "IOCL" in codes:
                cpcl_iocl += 1
            elif "IOCL" in codes and "BPCL" in codes:
                iocl_bpcl += 1
            elif "CPCL" in codes and "BPCL" in codes:
                cpcl_bpcl += 1
            elif "CPCL" in codes:
                cpcl_only += 1
            elif "IOCL" in codes:
                iocl_only += 1
            elif "BPCL" in codes:
                bpcl_only += 1

        return {
            "cpcl_only": cpcl_only,
            "iocl_only": iocl_only,
            "bpcl_only": bpcl_only,
            "cpcl_iocl": cpcl_iocl,
            "iocl_bpcl": iocl_bpcl,
            "cpcl_bpcl": cpcl_bpcl,
            "all_three": all_three
        }
