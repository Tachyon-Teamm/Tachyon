import re
import json
import pandas as pd
from typing import Dict, Any, Optional
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

def sanitize_price(raw_val: Any) -> float:
    """
    Safely converts arbitrary raw price strings (with commas, currency symbols ₹/$,
    scientific notation, and negative values) to float.
    """
    if raw_val is None or pd.isna(raw_val):
        return 0.0
    val_str = str(raw_val).strip()
    if not val_str or val_str.upper() in ["N/A", "NA", "NULL", "NONE", "-", "UNKNOWN"]:
        return 0.0
    val_str = val_str.replace(',', '')
    cleaned = re.sub(r'[^\d.eE+-]', '', val_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0

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
        if hasattr(batch, 'quality_score'):
            batch.quality_score = quality_report.quality_score
            db.commit()

        # Process records in memory-safe mini-batches of 64
        mini_batch_size = 64
        total_count = len(raw_records)

        for chunk_start in range(0, total_count, mini_batch_size):
            chunk = raw_records[chunk_start : chunk_start + mini_batch_size]
            
            # 1. Pre-extract specs and descriptions for the entire mini-batch
            batch_items = []
            batch_descriptions = []
            
            for raw in chunk:
                data = raw.raw_data or {}
                mat_code = str(data.get(mapping_config.get("material_code", "MATERIAL_NO"), f"TEMP-{raw.id}")).strip()
                desc = str(data.get(mapping_config.get("short_description", "ITEM_SPEC"), "")).strip()
                raw_uom = str(data.get(mapping_config.get("uom", "UOM"), "EA")).strip()
                raw_price = sanitize_price(data.get(mapping_config.get("base_price", "PRICE"), 0.0))
                raw_vendor = str(data.get(mapping_config.get("vendor_name", "VENDOR"), "")).strip()
                raw_hsn = str(data.get(mapping_config.get("hsn_code", "HSN"), "")).strip()

                multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc, raw_uom)
                uom_norm = UOMNormalizer.normalize_uom(raw_uom)
                specs = SpecExtractor.extract_specs(desc)
                specs["base_uom"] = base_uom
                specs["package_multiplier"] = multiplier
                norm_vendor = VendorNormalizer.normalize_vendor(raw_vendor)
                
                # Dynamic Schema-on-Read: capture all non-core spreadsheet columns into tech_attrs
                core_source_cols = {
                    mapping_config.get("material_code"),
                    mapping_config.get("short_description"),
                    mapping_config.get("uom"),
                    mapping_config.get("base_price"),
                    mapping_config.get("vendor_name"),
                    mapping_config.get("hsn_code")
                }
                tech_attrs = {}
                for k, v in data.items():
                    if k not in core_source_cols and v is not None and str(v).strip() != "":
                        clean_k = re.sub(r'[^a-zA-Z0-9_]', '_', str(k).strip().lower()).strip('_')
                        if clean_k:
                            tech_attrs[clean_k] = str(v).strip()
                            
                # Merge extracted specs with tech_attrs (spreadsheet column values take precedence over regex guesses)
                extracted_tech = dict(specs.get("technical_attributes") or {})
                extracted_tech.update(tech_attrs)
                tech_attrs = extracted_tech

                # Zero-Shot Taxonomy Categorization
                from app.services.matching.taxonomy_classifier import TaxonomyClassifier
                top_cats = TaxonomyClassifier.classify_description(db, desc, top_k=1)
                pred_cat = top_cats[0] if top_cats else {"code": "GENERAL", "name": "General Industrial", "confidence": 0.5}

                rec_completeness = 1.0 if (mat_code and desc and raw_uom) else 0.5
                if tech_attrs:
                    rec_completeness = min(1.0, rec_completeness + 0.2)

                canonical_text = EmbeddingService.build_canonical_text(specs, desc)

                batch_items.append({
                    "raw": raw,
                    "mat_code": mat_code,
                    "desc": desc,
                    "canonical_text": canonical_text,
                    "uom_norm": uom_norm,
                    "base_uom": base_uom,
                    "multiplier": multiplier,
                    "specs": specs,
                    "tech_attrs": tech_attrs,
                    "category_code": pred_cat.get("code", "GENERAL"),
                    "category_confidence": pred_cat.get("confidence", 1.0),
                    "predicted_category_name": pred_cat.get("name", ""),
                    "norm_vendor": norm_vendor,
                    "raw_vendor": raw_vendor,
                    "raw_price": raw_price,
                    "raw_hsn": raw_hsn,
                    "rec_completeness": rec_completeness
                })
                batch_descriptions.append(canonical_text or specs.get("raw_preprocessed") or desc or "ITEM")

            # 2. Vectorize the entire mini-batch simultaneously (PyTorch SIMD Tensor Acceleration)
            batch_vectors = EmbeddingService.generate_batch_embeddings(batch_descriptions)

            # 3. Pre-fetch existing entities for the mini-batch in bulk (eliminates N+1 queries)
            raw_ids_in_chunk = [it["raw"].id for it in batch_items]
            mat_codes_in_chunk = [it["mat_code"] for it in batch_items]

            existing_norms = {
                nm.raw_material_id: nm
                for nm in db.query(NormalizedMaterial).filter(NormalizedMaterial.raw_material_id.in_(raw_ids_in_chunk)).all()
            }
            existing_mats = {
                m.material_code: m
                for m in db.query(Material).filter(
                    Material.cpse_id == batch.cpse_id,
                    Material.material_code.in_(mat_codes_in_chunk)
                ).all()
            }
            existing_mat_ids = [m.id for m in existing_mats.values()]
            existing_embs = {
                me.material_id: me
                for me in db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id.in_(existing_mat_ids)).all()
            }
            existing_procs = {
                p.material_id: p
                for p in db.query(ProcurementHistory).filter(ProcurementHistory.material_id.in_(existing_mat_ids)).all()
            }

            # 4. Persist Silver, Gold, Vector, and Procurement entities with row-level bulkhead isolation
            for i, item in enumerate(batch_items):
                raw = item["raw"]
                try:
                    # Silver Layer
                    norm_mat = existing_norms.get(raw.id)
                    if not norm_mat:
                        norm_mat = NormalizedMaterial(
                            raw_material_id=raw.id,
                            cpse_id=batch.cpse_id,
                            material_code=item["mat_code"],
                            cleaned_description=item["specs"].get("raw_preprocessed") or item["desc"],
                            base_uom=item["base_uom"],
                            package_multiplier=item["multiplier"],
                            category_code=item["specs"].get("item_noun") or "GENERAL",
                            technical_attributes=item["tech_attrs"],
                            quality_score=round(item["rec_completeness"], 2),
                            status="PROMOTED"
                        )
                        db.add(norm_mat)

                    # Active Material (Gold)
                    mat = existing_mats.get(item["mat_code"])

                    if not mat:
                        mat = Material(
                            raw_material_id=raw.id,
                            cpse_id=batch.cpse_id,
                            material_code=item["mat_code"],
                            short_description=item["desc"],
                            uom=item["uom_norm"],
                            base_uom=item["base_uom"],
                            package_multiplier=item["multiplier"],
                            item_noun=item["specs"].get("item_noun"),
                            nominal_size=item["specs"].get("nominal_size"),
                            pressure_class=item["specs"].get("pressure_class"),
                            moc=item["specs"].get("moc"),
                            schedule=item["specs"].get("schedule"),
                            end_connection=item["specs"].get("end_connection"),
                            standard_spec=item["specs"].get("standard_spec"),
                            part_number=item["specs"].get("part_number"),
                            clean_part_number=item["specs"].get("clean_part_number"),
                            clearance_suffix=item["specs"].get("clearance_suffix"),
                            is_kit_or_assembly=item["specs"].get("is_kit_or_assembly", False),
                            category_code=item.get("category_code") or item["specs"].get("item_noun") or "GENERAL",
                            category_confidence=item.get("category_confidence", 1.0),
                            predicted_category_name=item.get("predicted_category_name"),
                            technical_attributes=item["tech_attrs"],
                            extracted_attributes=item["specs"],
                            status="ACTIVE"
                        )
                        db.add(mat)
                        db.flush()
                        existing_mats[item["mat_code"]] = mat
                    else:
                        mat.category_code = item.get("category_code") or mat.category_code
                        mat.category_confidence = item.get("category_confidence", mat.category_confidence)
                        mat.predicted_category_name = item.get("predicted_category_name") or mat.predicted_category_name
                        mat.technical_attributes = item["tech_attrs"]
                        mat.extracted_attributes = item["specs"]

                    # Vector Embedding (Bulkhead Protected)
                    try:
                        emb_vector = batch_vectors[i] if i < len(batch_vectors) else EmbeddingService.generate_embedding(item["canonical_text"])
                        mat_emb = existing_embs.get(mat.id)
                        if not mat_emb:
                            mat_emb = MaterialEmbedding(
                                material_id=mat.id,
                                embedding=emb_vector
                            )
                            db.add(mat_emb)
                            existing_embs[mat.id] = mat_emb
                        else:
                            mat_emb.embedding = emb_vector
                    except Exception as emb_err:
                        print(f"[Ingestion] Note: Embedding persistence skipped for mat {mat.id}: {emb_err}")

                    # Procurement History
                    proc = existing_procs.get(mat.id)
                    if not proc:
                        proc = ProcurementHistory(
                            material_id=mat.id,
                            cpse_id=batch.cpse_id,
                            vendor_name=item["raw_vendor"],
                            vendor_normalized=item["norm_vendor"],
                            hsn_code=item["raw_hsn"],
                            unit_price=item["raw_price"],
                            quantity=1.0,
                            total_spend=item["raw_price"]
                        )
                        db.add(proc)
                        existing_procs[mat.id] = proc

                    processed += 1

                except Exception as item_err:
                    print(f"[Ingestion] Row {raw.id} failed during normalization: {item_err}")
                    err_norm = NormalizedMaterial(
                        raw_material_id=raw.id,
                        cpse_id=batch.cpse_id,
                        material_code=item.get("mat_code", f"ERR-{raw.id}"),
                        cleaned_description=item.get("desc", ""),
                        status="ERROR",
                        quality_score=0.0
                    )
                    db.add(err_norm)
                    processed += 1

            # Update batch progress in DB after each chunk
            batch.processed_rows = processed
            db.commit()

        batch.processed_rows = processed
        batch.status = "COMPLETED"
        if hasattr(batch, 'quality_score'):
            batch.quality_score = quality_report.quality_score
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
