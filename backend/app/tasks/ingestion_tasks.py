import json
import pandas as pd
from typing import Dict, Any
from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db
from app.models.models import (
    IngestionBatch, RawMaterial, NormalizedMaterial, Material, 
    MaterialEmbedding, ProcurementHistory
)
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.domain_lexicon import DomainLexicon
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.normalization.data_profiler import DataProfiler
from app.services.matching.embeddings import EmbeddingService

@celery_app.task(name="process_ingestion_batch_task")
def process_ingestion_batch_task(batch_id: int, mapping_config: Dict[str, str]):
    db = next(get_sync_db())
    batch = db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
    if not batch:
        return {"error": "Batch not found"}

    try:
        batch.status = "PROCESSING"
        db.commit()

        raw_records = db.query(RawMaterial).filter(RawMaterial.batch_id == batch_id).all()
        processed = 0

        # Profile batch quality
        batch_dicts = []
        for r in raw_records:
            d = r.raw_data or {}
            batch_dicts.append({
                "material_code": d.get(mapping_config.get("material_code", "MATERIAL_NO")),
                "short_description": d.get(mapping_config.get("short_description", "ITEM_SPEC")),
                "uom": d.get(mapping_config.get("uom", "UOM"))
            })
        quality_report = DataProfiler.profile_records(batch_dicts)

        for raw in raw_records:
            data = raw.raw_data
            
            # Map columns
            mat_code = str(data.get(mapping_config.get("material_code", "MATERIAL_NO"), f"TEMP-{raw.id}")).strip()
            desc = str(data.get(mapping_config.get("short_description", "ITEM_SPEC"), "")).strip()
            raw_uom = str(data.get(mapping_config.get("uom", "UOM"), "EA")).strip()
            raw_price = float(data.get(mapping_config.get("base_price", "PRICE"), 0.0) or 0.0)
            raw_vendor = str(data.get(mapping_config.get("vendor_name", "VENDOR"), "")).strip()
            raw_hsn = str(data.get(mapping_config.get("hsn_code", "HSN"), "")).strip()

            # Normalization & Parametric Spec Extraction
            multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc, raw_uom)
            uom_norm = UOMNormalizer.normalize_uom(raw_uom)
            specs = SpecExtractor.extract_specs(desc)
            specs["base_uom"] = base_uom
            specs["package_multiplier"] = multiplier
            
            norm_vendor = VendorNormalizer.normalize_vendor(raw_vendor)
            tech_attrs = specs.get("technical_attributes") or {}

            # Calculate individual record completeness score
            rec_completeness = 1.0 if (mat_code and desc and raw_uom) else 0.5
            if tech_attrs:
                rec_completeness = min(1.0, rec_completeness + 0.2)

            # 1. Silver Layer: Normalized & Cleansed Material Staging
            norm_mat = db.query(NormalizedMaterial).filter(
                NormalizedMaterial.raw_material_id == raw.id
            ).first()
            if not norm_mat:
                norm_mat = NormalizedMaterial(
                    raw_material_id=raw.id,
                    cpse_id=batch.cpse_id,
                    material_code=mat_code,
                    cleaned_description=specs.get("raw_preprocessed") or desc,
                    base_uom=base_uom,
                    package_multiplier=multiplier,
                    category_code=specs.get("item_noun") or "GENERAL",
                    technical_attributes=tech_attrs,
                    quality_score=round(rec_completeness, 2),
                    status="PROMOTED"
                )
                db.add(norm_mat)

            # 2. Promote to Active Material record
            mat = db.query(Material).filter(
                Material.cpse_id == batch.cpse_id,
                Material.material_code == mat_code
            ).first()

            if not mat:
                mat = Material(
                    raw_material_id=raw.id,
                    cpse_id=batch.cpse_id,
                    material_code=mat_code,
                    short_description=desc,
                    uom=uom_norm,
                    base_uom=base_uom,
                    package_multiplier=multiplier,
                    item_noun=specs.get("item_noun"),
                    nominal_size=specs.get("nominal_size"),
                    pressure_class=specs.get("pressure_class"),
                    moc=specs.get("moc"),
                    schedule=specs.get("schedule"),
                    end_connection=specs.get("end_connection"),
                    standard_spec=specs.get("standard_spec"),
                    part_number=specs.get("part_number"),
                    clean_part_number=specs.get("clean_part_number"),
                    clearance_suffix=specs.get("clearance_suffix"),
                    is_kit_or_assembly=specs.get("is_kit_or_assembly", False),
                    technical_attributes=tech_attrs,
                    extracted_attributes=specs,
                    status="ACTIVE"
                )
                db.add(mat)
                db.flush()
            else:
                mat.technical_attributes = tech_attrs
                mat.extracted_attributes = specs

            # Generate embedding vector
            emb_vector = EmbeddingService.generate_embedding(desc)
            mat_emb = db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == mat.id).first()
            if not mat_emb:
                mat_emb = MaterialEmbedding(
                    material_id=mat.id,
                    embedding=emb_vector
                )
                db.add(mat_emb)

            # Record Procurement History
            proc = db.query(ProcurementHistory).filter(ProcurementHistory.material_id == mat.id).first()
            if not proc:
                proc = ProcurementHistory(
                    material_id=mat.id,
                    cpse_id=batch.cpse_id,
                    vendor_name=raw_vendor,
                    vendor_normalized=norm_vendor,
                    hsn_code=raw_hsn,
                    unit_price=raw_price,
                    quantity=1.0,
                    total_spend=raw_price
                )
                db.add(proc)

            processed += 1
            if processed % 100 == 0:
                batch.processed_rows = processed
                db.commit()

        batch.processed_rows = processed
        batch.status = "COMPLETED"
        db.commit()
        return {
            "status": "SUCCESS", 
            "processed_rows": processed,
            "quality_score": quality_report.quality_score,
            "completeness_rate": quality_report.completeness_rate
        }

    except Exception as e:
        db.rollback()
        batch.status = "FAILED"
        batch.error_message = str(e)
        db.commit()
        raise e
    finally:
        db.close()
