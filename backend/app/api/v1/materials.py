from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_, and_
from app.core.database import get_db
from app.models.models import Material, CPSE, ProcurementHistory
from app.schemas.schemas import MaterialResponse

router = APIRouter(prefix="/materials", tags=["Materials Master"])

@router.get("", response_model=List[MaterialResponse])
async def get_materials(
    cpse_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    item_noun: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = select(Material).options(
        joinedload(Material.cpse),
        joinedload(Material.procurement_records)
    )
    
    if cpse_code:
        query = query.join(Material.cpse).filter(CPSE.code == cpse_code.upper())
            
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Material.material_code.ilike(s),
                Material.short_description.ilike(s),
                Material.clean_part_number.ilike(s)
            )
        )
        
    if item_noun:
        query = query.filter(Material.item_noun.ilike(f"%{item_noun}%"))
        
    query = query.order_by(Material.id.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    materials = res.scalars().unique().all()
    
    out = []
    for m in materials:
        cpse = m.cpse
        proc = m.procurement_records[0] if (m.procurement_records and len(m.procurement_records) > 0) else None
        
        out.append(MaterialResponse(
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
        ))
    return out

@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material_detail(material_id: int, db: Session = Depends(get_db)):
    res = await db.execute(select(Material).filter(Material.id == material_id))
    m = res.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
        
    cpse_res = await db.execute(select(CPSE).filter(CPSE.id == m.cpse_id))
    cpse = cpse_res.scalars().first()
    proc_res = await db.execute(select(ProcurementHistory).filter(ProcurementHistory.material_id == m.id))
    proc = proc_res.scalars().first()
    
    return MaterialResponse(
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
