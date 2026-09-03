import csv
import io
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import Crosswalk, CNMCCode, GoldenRecord, Material, CPSE, ProcurementHistory

class SAPExportService:
    """
    SAP S/4HANA & ECC 6.0 Data Migration Export Service.
    Generates LSMW (Legacy System Migration Workbench) and LTMC (Migration Cockpit) formats.
    """

    @classmethod
    def generate_lsmw_csv(cls, db: Session, cpse_code: Optional[str] = None) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Standard SAP LSMW Material Master Basic Data 1 & 2 Structure (MARA / MAKT)
        headers = [
            "RECORD_TYPE",
            "CNMC_NATIONAL_CODE",
            "CPSE_LOCAL_CODE",
            "CPSE_ORG",
            "MATERIAL_TYPE",
            "INDUSTRY_SECTOR",
            "MATERIAL_DESCRIPTION_ISO8000",
            "BASE_UOM",
            "MATERIAL_GROUP_UNSPSC",
            "OLD_MATERIAL_NUMBER",
            "MAPPING_CONFIDENCE_TYPE",
            "GROSS_WEIGHT",
            "WEIGHT_UNIT",
            "LONG_TEXT_ISO8000"
        ]
        writer.writerow(headers)
        
        query = db.query(Crosswalk).join(Crosswalk.cnmc).join(CNMCCode.golden_record).join(Crosswalk.material).join(Crosswalk.cpse)
        if cpse_code:
            query = query.filter(CPSE.code == cpse_code.upper())
            
        rows = query.all()
        for r in rows:
            cnmc = r.cnmc
            golden = cnmc.golden_record if cnmc else None
            mat = r.material
            cpse = r.cpse
            
            full_desc = (golden.standardized_description if golden else (mat.short_description if mat else ""))
            short_desc = full_desc[:40] if full_desc else ""
            base_uom = (golden.base_uom if golden else (mat.base_uom if mat else "EA")) or "EA"
            cat_code = (golden.category_code if golden else None) or (mat.category_code if mat else None) or "40141600"
            pkg_mult = str(mat.package_multiplier if (mat and mat.package_multiplier is not None) else "1.0")
            weight_unit = "KG" if (mat and mat.base_uom == "KG") else "EA"

            writer.writerow([
                "MM01",                                # SAP T-Code
                cnmc.code if cnmc else "",             # National Authority Code
                r.local_material_code or "",           # Local CPSE Code
                cpse.code if cpse else "UNK",          # CPCL / IOCL / BPCL
                "ERSA",                                # Spare Parts Material Type
                "M",                                   # Mechanical Engineering
                short_desc,                            # SAP 40-char limit
                base_uom,
                cat_code,
                r.local_material_code or "",
                r.mapping_type or "IDENTICAL",
                pkg_mult,
                weight_unit,
                full_desc                              # Full untruncated ISO 8000 specification
            ])
            
        return output.getvalue()
