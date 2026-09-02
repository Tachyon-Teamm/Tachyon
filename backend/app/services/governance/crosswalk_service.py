from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
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
        siblings = db.query(Crosswalk).filter(Crosswalk.cnmc_id == cnmc.id).all()
        links = []
        total_vol = 0.0
        total_spend = 0.0
        normalized_prices = []
        
        for sib in siblings:
            mat = sib.material
            cpse = sib.cpse
            proc = db.query(ProcurementHistory).filter(ProcurementHistory.material_id == mat.id).first() if mat else None
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
                "created_at": golden.created_at if golden else None
            },
            "crosswalk_links": links,
            "total_spend": total_spend,
            "total_volume": total_vol,
            "potential_savings": potential_savings,
            "issued_at": cnmc.issued_at
        }

    @classmethod
    def reverse_lookup(cls, db: Session, local_code: str, cpse_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = db.query(Crosswalk).join(Material).join(CPSE).join(CNMCCode).join(GoldenRecord)
        
        if cpse_code:
            query = query.filter(CPSE.code == cpse_code.upper())
            
        cw_entry = query.filter(Crosswalk.local_material_code == local_code).first()
        if not cw_entry or not cw_entry.cnmc:
            return None

        return cls.format_cnmc_detail(db, cw_entry.cnmc)

