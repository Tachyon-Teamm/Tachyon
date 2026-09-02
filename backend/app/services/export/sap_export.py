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
            "WEIGHT_UNIT"
        ]
        writer.writerow(headers)
        
        query = db.query(Crosswalk).join(Crosswalk.cnmc).join(CNMCCode.golden_record).join(Crosswalk.material).join(Crosswalk.cpse)
        if cpse_code:
            query = query.filter(CPSE.code == cpse_code.upper())
            
        rows = query.all()
        for r in rows:
            cnmc = r.cnmc
            golden = cnmc.golden_record
            mat = r.material
            cpse = r.cpse
            
            writer.writerow([
                "MM01",                                # SAP T-Code
                cnmc.code,                             # National Authority Code
                r.local_material_code,                 # Local CPSE Code
                cpse.code,                             # CPCL / IOCL / BPCL
                "ERSA",                                # Spare Parts Material Type
                "M",                                   # Mechanical Engineering
                golden.standardized_description[:40] if golden else mat.short_description[:40],  # SAP 40-char limit
                golden.base_uom if golden else (mat.base_uom or "EA"),
                "40141600",                            # UNSPSC Group
                r.local_material_code,
                r.mapping_type,
                mat.package_multiplier if mat.base_uom == "KG" else "1.0",
                "KG" if mat.base_uom == "KG" else "EA"
            ])
            
        return output.getvalue()
