from typing import Dict, Any, List, Optional
import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_sync_session
from app.models.models import GoldenRecord, CNMCCode

router = APIRouter(prefix="/integration/gem", tags=["GeM Integration"])

@router.post("/catalog-sync")
def sync_gem_catalog(
    cnmc_codes: Optional[List[str]] = None,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Government e-Marketplace (GeM) Catalog Syndication API:
    Formats National Golden Records into GeM-compliant catalog items with Golden Parameters
    and PKI/DSC signature verification hashes.
    """
    close_db = False
    if db is None:
        sync_db = get_sync_session()
        close_db = True
    else:
        sync_db = db

    try:
        query = sync_db.query(GoldenRecord).join(CNMCCode)
        if cnmc_codes:
            query = query.filter(CNMCCode.code.in_(cnmc_codes))

        records = query.all()
        synced_items = []

        for r in records:
            cnmc_code = r.cnmc_code.code if r.cnmc_code else f"CNMC-TEMP-{r.id}"
            tech_attrs = r.technical_attributes if r.technical_attributes is not None else r.canonical_attributes
            if not isinstance(tech_attrs, dict):
                tech_attrs = {}

            # Map to GeM Golden Parameters
            gem_payload = {
                "gem_category": r.item_noun,
                "national_material_code": cnmc_code,
                "title": r.standardized_description,
                "base_uom": r.base_uom or "EA",
                "golden_parameters": {
                    "nominal_size": r.nominal_size or tech_attrs.get("nominal_size"),
                    "pressure_class": r.pressure_class or tech_attrs.get("pressure_class"),
                    "material_grade": r.moc or tech_attrs.get("moc"),
                    "standard_specification": r.standard_spec or tech_attrs.get("standard_spec"),
                    "end_connection": r.end_connection or tech_attrs.get("end_connection"),
                    "voltage_rating": tech_attrs.get("voltage_rating"),
                    "current_rating": tech_attrs.get("current_rating"),
                    "thread_size": tech_attrs.get("thread_size"),
                },
                "version": r.version_number,
                "syndicated_at": datetime.now(timezone.utc).isoformat()
            }

            # Generate PKI/DSC Compliance Signature Hash
            payload_str = json.dumps(gem_payload, sort_keys=True)
            gem_payload["pki_signature_hash"] = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            synced_items.append(gem_payload)

        return {
            "status": "SUCCESS",
            "total_syndicated": len(synced_items),
            "gem_catalog_items": synced_items
        }
    finally:
        if close_db:
            sync_db.close()
