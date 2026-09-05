#!/usr/bin/env python3
"""
UniMM Synthetic Data Ingestion & Demo Runner
Problem Statement 26099: AI-Driven Standardization and Harmonization of Material Codes Across CPSEs
Host Organization: Chennai Petroleum Corporation Limited (CPCL) / MoPNG
"""

import os
import sys
import argparse
import glob
import re
import pandas as pd
from typing import Dict, Any

# Ensure project root in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import SyncSessionLocal
from app.models.models import (
    CPSE, IngestionBatch, RawMaterial, MatchJob, MatchCandidate, ReviewQueue,
    GoldenRecord, CNMCCode, Crosswalk
)
from app.tasks.ingestion_tasks import process_ingestion_batch_task
from app.services.matching.matcher_engine import MatcherEngine
from app.services.governance.golden_record_service import GoldenRecordService
from app.services.governance.cnmc_minter import CNMCMinter
from app.services.governance.crosswalk_service import CrosswalkService

# Target file to CPSE mapping
FILE_CPSE_MAP = {
    "cpcl_materials.csv": "CPCL",
    "iocl_materials.csv": "IOCL",
    "bpcl_materials.csv": "BPCL",
    "ongc_materials.csv": "ONGC",
    "ntpc_materials.csv": "NTPC",
    "sail_materials.csv": "SAIL",
    "bhel_materials.csv": "BHEL",
    "coalindia_materials.csv": "COALINDIA",
}

STANDARD_SYNONYMS = {
    "material_code": ["MATERIAL_NO", "SAP_MATNR", "ITEM_CODE", "MATERIAL_NUMBER", "ITEM_NO", "MAT_NO", "PART_NO"],
    "short_description": ["ITEM_SPEC", "MATERIAL_DESC", "SHORT_TEXT", "ITEM_DESCRIPTION", "DESCRIPTION", "DESC"],
    "uom": ["UNIT_OF_MEASURE", "BASE_UOM", "UOM", "MEASURE_UNIT", "UNIT"],
    "base_price": ["LAST_PO_PRICE", "NETPR", "UNIT_PRICE", "PO_PRICE"],
    "quantity": ["QUANTITY", "PO_QTY", "ANNUAL_DEMAND"],
    "vendor_name": ["VENDOR_NAME", "SUPPLIER_NAME", "VENDOR"],
    "hsn_code": ["HSN_CODE", "COMMODITY_CODE", "HSN"]
}

def auto_detect_mapping(df_columns):
    mapping = {}
    assigned_targets = set()
    cols = [str(c).strip() for c in df_columns]
    
    for c in cols:
        c_upper = c.upper()
        c_clean = re.sub(r"[^A-Z0-9]", "_", c_upper).strip("_")
        matched = False
        for target, syn_list in STANDARD_SYNONYMS.items():
            if target in assigned_targets:
                continue
            if c_upper in syn_list or c_clean in syn_list:
                mapping[c] = target
                assigned_targets.add(target)
                matched = True
                break
        if not matched:
            mapping[c] = "unmapped"
    return mapping

def run_ingestion(auto_approve: bool = False, clean: bool = False, dataset_dir: str = "data/synthetic_datasets"):
    db = SyncSessionLocal()
    try:
        print("=" * 75)
        print("   UniMM Synthetic Data Ingestion Runner — Problem Statement 26099")
        print("   Chennai Petroleum Corporation Limited (CPCL) / MoPNG")
        print("=" * 75)

        if clean:
            print("[*] Cleaning existing transactional and material records...")
            tables = [
                "audit_log", "material_substitutions", "review_feedback", "crosswalk",
                "cnmc_codes", "golden_record_versions", "golden_records", "review_queue",
                "match_candidates", "match_jobs", "legacy_migration_states",
                "procurement_history", "material_classifications", "material_embeddings",
                "materials", "normalized_materials", "raw_materials", "column_mappings",
                "ingestion_batches"
            ]
            for t in tables:
                db.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE;"))
            db.commit()
            print(" [+] Database clean completed.")

        if not os.path.isabs(dataset_dir):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            dataset_dir = os.path.join(base_dir, dataset_dir)

        # 1. Ingest Batches
        total_ingested_files = 0
        total_materials_ingested = 0

        csv_files = sorted(glob.glob(os.path.join(dataset_dir, "*.csv")))
        if not csv_files:
            print(f"Error: No CSV files found in {dataset_dir}")
            return

        for csv_path in csv_files:
            filename = os.path.basename(csv_path)
            cpse_code = FILE_CPSE_MAP.get(filename)
            if not cpse_code:
                continue

            cpse = db.query(CPSE).filter(CPSE.code == cpse_code).first()
            if not cpse:
                print(f"[!] CPSE {cpse_code} not found in database. Skipping {filename}.")
                continue

            df = pd.read_csv(csv_path, index_col=False)
            mapping = auto_detect_mapping(df.columns)

            batch = IngestionBatch(
                cpse_id=cpse.id,
                file_name=filename,
                file_size_bytes=os.path.getsize(csv_path),
                total_rows=len(df),
                processed_rows=0,
                status="PROCESSING"
            )
            db.add(batch)
            db.flush()

            # Insert raw records
            for idx, row in df.iterrows():
                raw_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                db.add(RawMaterial(
                    batch_id=batch.id,
                    cpse_id=cpse.id,
                    row_index=int(idx),
                    raw_data=raw_dict
                ))
            db.commit()

            # Execute pipeline normalization & embedding task
            process_ingestion_batch_task(batch.id, mapping)
            total_ingested_files += 1
            total_materials_ingested += len(df)
            print(f" [+] Ingested & Normalized: {cpse_code:10} | {filename:22} | {len(df):2} records")

        print("-" * 75)
        print(f"Total: {total_ingested_files} CPSE files ingested ({total_materials_ingested} master items)")

        # 2. Trigger Cross-CPSE Matching
        print("\n[*] Triggering Cross-Enterprise AI Matching & Safety Invariant Engine...")
        match_job = MatchJob(
            status="RUNNING",
            total_pairs_evaluated=0,
            candidates_found=0
        )
        db.add(match_job)
        db.commit()

        result = MatcherEngine.execute_cross_cpse_matching(db, match_job.id)
        pairs_eval = result.get("pairs_evaluated", 0)
        clusters_form = result.get("clusters_formed", 0)
        cands_found = result.get("candidates_found", 0)
        print(f" [+] Pairs Evaluated:   {pairs_eval}")
        print(f" [+] Clusters Formed:   {clusters_form}")
        print(f" [+] Candidates Found: {cands_found}")

        # 3. Optional Auto-Approve for Instant Dashboard Populate
        if auto_approve:
            print("\n[*] Fast-Tracking High-Confidence Clusters (Auto-Approve)...")
            pending_rqs = db.query(ReviewQueue).filter(
                ReviewQueue.status == "PENDING",
                ReviewQueue.confidence_tier == "HIGH"
            ).all()

            approved_cnt = 0
            for rq in pending_rqs:
                cands = db.query(MatchCandidate).filter(MatchCandidate.cluster_group_id == rq.cluster_group_id).all()
                if any(c.safety_veto for c in cands):
                    continue

                mat_ids = set()
                for c in cands:
                    mat_ids.add(c.material_a_id)
                    mat_ids.add(c.material_b_id)

                from app.models.models import Material
                mats = db.query(Material).filter(Material.id.in_(list(mat_ids))).all()
                if not mats:
                    continue

                synth = GoldenRecordService.synthesize_iso8000_description(mats)
                golden = GoldenRecord(
                    review_queue_id=rq.id,
                    standardized_description=synth["standardized_description"],
                    item_noun=synth["item_noun"],
                    modifier=synth["modifier"],
                    nominal_size=synth["nominal_size"],
                    pressure_class=synth["pressure_class"],
                    moc=synth["moc"],
                    schedule=synth["schedule"],
                    end_connection=synth["end_connection"],
                    standard_spec=synth["standard_spec"],
                    base_uom=synth["base_uom"],
                    technical_attributes=synth.get("technical_attributes", {}),
                    canonical_attributes=synth.get("canonical_attributes", {})
                )
                db.add(golden)
                db.flush()

                cnmc_code = CNMCMinter.mint_next_cnmc(db, golden.id)
                cnmc_obj = db.query(CNMCCode).filter(CNMCCode.code == cnmc_code).first()
                CrosswalkService.register_mappings(db, cnmc_obj.id, mats, mapping_type="IDENTICAL")

                rq.status = "APPROVED"
                rq.decision_type = "IDENTICAL"
                rq.reviewer_notes = "Automated batch validation"
                approved_cnt += 1

            db.commit()
            print(f" [+] Minted {approved_cnt} Verhoeff-checksummed CNMC Golden Records!")
            print(f" [+] Crosswalk Hub links and Demand Aggregation table active.")

        print("=" * 75)
        print("Demo Environment Ready! You can now start the web UI and explore.")
        print("  Backend:  http://localhost:8000")
        print("  Frontend: http://localhost:3000")
        print("=" * 75)

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest UniMM Synthetic Data")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve high confidence clusters")
    parser.add_argument("--clean", action="store_true", help="Clean/truncate existing materials and transactions before ingestion")
    parser.add_argument("--dataset-dir", default="data/synthetic_datasets", help="Directory containing CSV files")
    args = parser.parse_args()

    run_ingestion(auto_approve=args.auto_approve, clean=args.clean, dataset_dir=args.dataset_dir)
