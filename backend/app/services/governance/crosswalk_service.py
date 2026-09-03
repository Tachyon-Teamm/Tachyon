from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.models import Crosswalk, CNMCCode, Material, CPSE, GoldenRecord, ProcurementHistory

class CrosswalkService:
    """
    Unified Crosswalk Hub (N:1 Link).
    Maps local CPCL, IOCL, BPCL codes to a single National CNMC authority code.
    """

    @classmethod
    def register_mappings(
        cls,
        db: Session,
        cnmc_id: int,
        materials: List[Material],
        mapping_type: str = "IDENTICAL"
    ) -> List[Crosswalk]:
        entries = []
        for m in materials:
            # Check if mapping already exists
            existing = db.query(Crosswalk).filter(
                Crosswalk.cnmc_id == cnmc_id,
                Crosswalk.cpse_id == m.cpse_id,
                Crosswalk.local_material_code == m.material_code
            ).first()
            
            if not existing:
                cw = Crosswalk(
                    cnmc_id=cnmc_id,
                    cpse_id=m.cpse_id,
                    material_id=m.id,
                    local_material_code=m.material_code,
                    mapping_type=mapping_type,
                    is_active=True
                )
                db.add(cw)
                entries.append(cw)
        db.flush()
        return entries

    @classmethod
    def format_cnmc_detail(cls, db: Session, cnmc: CNMCCode) -> Dict[str, Any]:
        golden = cnmc.golden_record
        # Bulk eager load siblings with material and cpse to eliminate N+1 queries
        siblings = db.query(Crosswalk).options(
            joinedload(Crosswalk.material),
            joinedload(Crosswalk.cpse)
        ).filter(Crosswalk.cnmc_id == cnmc.id).all()

        # Pre-fetch all procurement records in a single query
        mat_ids = [sib.material_id for sib in siblings if sib.material_id]
        proc_records = (
            db.query(ProcurementHistory)
            .filter(ProcurementHistory.material_id.in_(mat_ids))
            .all()
            if mat_ids else []
        )
        proc_map: Dict[int, ProcurementHistory] = {pr.material_id: pr for pr in proc_records}

        links = []
        total_vol = 0.0
        total_spend = 0.0
        normalized_prices = []
        
        for sib in siblings:
            mat = sib.material
            cpse = sib.cpse
            proc = proc_map.get(mat.id) if mat else None
            price = proc.unit_price if (proc and proc.unit_price is not None) else 0.0
            qty = proc.quantity if (proc and proc.quantity is not None) else 0.0
            multiplier = (mat.package_multiplier if mat and mat.package_multiplier else 1.0) or 1.0
            
            unit_price_norm = (price / multiplier) if (multiplier > 0 and price > 0) else price
            item_vol = qty * multiplier
            
            if unit_price_norm > 0:
                normalized_prices.append(unit_price_norm)
                
            total_vol += item_vol
            total_spend += (price * qty)

            links.append({
                "cpse_code": cpse.code if cpse else "UNKNOWN",
                "local_material_code": sib.local_material_code,
                "short_description": mat.short_description if mat else "",
                "mapping_type": sib.mapping_type,
                "last_po_price": price,
                "normalized_unit_price": unit_price_norm,
                "volume": item_vol,
                "uom": mat.uom if mat else "EA"
            })

        potential_savings = 0.0
        if len(normalized_prices) > 1 and max(normalized_prices) > min(normalized_prices):
            best_unit_price = min(normalized_prices)
            for l in links:
                p = l.get("normalized_unit_price", 0.0)
                v = l.get("volume", 0.0)
                if p > best_unit_price and v > 0:
                    potential_savings += (p - best_unit_price) * v

        issued_ts = cnmc.issued_at or datetime.now(timezone.utc)
        created_ts = (golden.created_at if (golden and golden.created_at) else issued_ts)

        return {
            "cnmc_code": cnmc.code,
            "golden_record": {
                "id": golden.id if golden else 0,
                "standardized_description": golden.standardized_description if golden else "",
                "item_noun": golden.item_noun if golden else "",
                "modifier": golden.modifier if golden else "",
                "nominal_size": golden.nominal_size if golden else "",
                "pressure_class": golden.pressure_class if golden else "",
                "moc": golden.moc if golden else "",
                "schedule": golden.schedule if golden else "",
                "end_connection": golden.end_connection if golden else "",
                "standard_spec": golden.standard_spec if golden else "",
                "base_uom": golden.base_uom if golden else "EA",
                "created_at": created_ts
            },
            "crosswalk_links": links,
            "total_spend": total_spend,
            "total_volume": total_vol,
            "potential_savings": potential_savings,
            "issued_at": issued_ts
        }

    @classmethod
    def reverse_lookup(cls, db: Session, local_code: str, cpse_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query_str = local_code.strip()
        if not query_str:
            return None

        # 1. Bidirectional Check: Did the user provide a National CNMC Code?
        if query_str.upper().startswith("CNMC-"):
            cnmc_direct = (
                db.query(CNMCCode)
                .options(joinedload(CNMCCode.golden_record))
                .filter(func.upper(CNMCCode.code) == query_str.upper())
                .first()
            )
            if cnmc_direct:
                return cls.format_cnmc_detail(db, cnmc_direct)

        # 2. Local Material Code Lookup with Eager Relationships
        query = (
            db.query(Crosswalk)
            .options(
                joinedload(Crosswalk.cnmc).joinedload(CNMCCode.golden_record),
                joinedload(Crosswalk.material),
                joinedload(Crosswalk.cpse)
            )
        )
        
        if cpse_code:
            query = query.join(Crosswalk.cpse).filter(func.upper(CPSE.code) == cpse_code.upper())
            
        cw_entry = query.filter(func.upper(Crosswalk.local_material_code) == query_str.upper()).first()
        if cw_entry and cw_entry.cnmc:
            return cls.format_cnmc_detail(db, cw_entry.cnmc)

        # 3. Fallback: Check if query matches a CNMC code without "CNMC-" prefix
        cnmc_fallback = (
            db.query(CNMCCode)
            .options(joinedload(CNMCCode.golden_record))
            .filter(func.upper(CNMCCode.code) == query_str.upper())
            .first()
        )
        if cnmc_fallback:
            return cls.format_cnmc_detail(db, cnmc_fallback)

        return None

