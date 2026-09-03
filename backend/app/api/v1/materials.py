from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_, and_, func
from app.core.database import get_db
from app.models.models import Material, CPSE, ProcurementHistory
from app.schemas.schemas import MaterialResponse, PaginatedMaterialResponse, CPSEResponse

router = APIRouter(prefix="/materials", tags=["Materials Master"])

@router.get("/refineries/list", response_model=List[CPSEResponse])
async def list_refineries(db: Session = Depends(get_db)):
    """Fetch all active CPSEs / refineries dynamically for catalog filtering."""
    res = await db.execute(select(CPSE).filter(CPSE.is_active == True).order_by(CPSE.code.asc()))
    return res.scalars().all()

@router.get("", response_model=Union[PaginatedMaterialResponse, List[MaterialResponse]])
async def get_materials(
    cpse_code: Optional[str] = Query(None, description="Filter by CPSE code (e.g. CPCL, IOCL, BPCL)"),
    search: Optional[str] = Query(None, description="Multi-attribute search across code, description, noun, specs, and part no"),
    item_noun: Optional[str] = Query(None, description="Direct filter by extracted item noun"),
    page: Optional[int] = Query(None, ge=1, description="1-based page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Legacy limit override"),
    offset: Optional[int] = Query(None, ge=0, description="Legacy offset override"),
    db: Session = Depends(get_db)
):
    # Support legacy limit/offset overrides while defaulting to clean page/page_size
    effective_limit = limit if limit is not None else page_size
    effective_offset = offset if offset is not None else (page - 1) * effective_limit
    effective_page = (effective_offset // effective_limit) + 1 if effective_limit > 0 else 1

    # Base search filter clauses
    search_filters = []
    if search and search.strip():
        s = f"%{search.strip()}%"
        search_filters.append(
            or_(
                Material.material_code.ilike(s),
                Material.short_description.ilike(s),
                Material.clean_part_number.ilike(s),
                Material.item_noun.ilike(s),
                Material.moc.ilike(s),
                Material.schedule.ilike(s),
                Material.standard_spec.ilike(s),
                Material.nominal_size.ilike(s),
            )
        )
    if item_noun and item_noun.strip():
        search_filters.append(Material.item_noun.ilike(f"%{item_noun.strip()}%"))

    # 1. Total Count Query (single lightweight query with matching filters)
    count_query = select(func.count(Material.id))
    if cpse_code and cpse_code.strip():
        count_query = count_query.join(Material.cpse).filter(CPSE.code == cpse_code.strip().upper())
    for flt in search_filters:
        count_query = count_query.filter(flt)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # 2. Main Data Query with Eager Joined Loading (Eliminates N+1 query loops)
    query = select(Material).options(
        joinedload(Material.cpse),
        joinedload(Material.procurement_records)
    )
    if cpse_code and cpse_code.strip():
        query = query.join(Material.cpse).filter(CPSE.code == cpse_code.strip().upper())
    for flt in search_filters:
        query = query.filter(flt)

    query = query.order_by(Material.id.desc()).offset(effective_offset).limit(effective_limit)
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

    total_pages = (total + effective_limit - 1) // effective_limit if total > 0 else 1

    if page is not None or limit is None:
        return PaginatedMaterialResponse(
            items=out,
            total=total,
            page=effective_page,
            page_size=effective_limit,
            total_pages=total_pages
        )
    return out

@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material_detail(material_id: int, db: Session = Depends(get_db)):
    """Fetch single material record with single-query eager joined relationships."""
    res = await db.execute(
        select(Material)
        .options(
            joinedload(Material.cpse),
            joinedload(Material.procurement_records)
        )
        .filter(Material.id == material_id)
    )
    m = res.scalars().unique().first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
        
    cpse = m.cpse
    proc = m.procurement_records[0] if (m.procurement_records and len(m.procurement_records) > 0) else None
    
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
