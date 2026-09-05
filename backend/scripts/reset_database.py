import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import sync_engine
import redis

def reset_all_data():
    print("=== UniMM Fresh Reset Protocol ===")
    
    tables_to_truncate = [
        "audit_log",
        "material_substitutions",
        "review_feedback",
        "crosswalk",
        "cnmc_codes",
        "golden_record_versions",
        "golden_records",
        "review_queue",
        "match_candidates",
        "match_jobs",
        "legacy_migration_states",
        "procurement_history",
        "material_classifications",
        "material_embeddings",
        "materials",
        "normalized_materials",
        "raw_materials",
        "column_mappings",
        "ingestion_batches"
    ]
    
    with sync_engine.begin() as conn:
        for tbl in tables_to_truncate:
            try:
                conn.execute(text(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE;"))
                print(f"  [OK] Cleared table: {tbl}")
            except Exception as e:
                print(f"  [WARN] Could not truncate {tbl}: {e}")
                
    # Flush Redis cache
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.Redis.from_url(redis_url)
        r.flushdb()
        print("  [OK] Redis database flushed.")
    except Exception as e:
        print(f"  [WARN] Redis flush notice: {e}")
        
    # Verify counts
    with sync_engine.connect() as conn:
        mat_count = conn.execute(text("SELECT COUNT(*) FROM materials;")).scalar()
        cnmc_count = conn.execute(text("SELECT COUNT(*) FROM cnmc_codes;")).scalar()
        rev_count = conn.execute(text("SELECT COUNT(*) FROM review_queue;")).scalar()
        batch_count = conn.execute(text("SELECT COUNT(*) FROM ingestion_batches;")).scalar()
        cpse_count = conn.execute(text("SELECT COUNT(*) FROM cpses;")).scalar()
        user_count = conn.execute(text("SELECT COUNT(*) FROM users;")).scalar()
        tax_count = conn.execute(text("SELECT COUNT(*) FROM taxonomy_categories;")).scalar()
        
        print("\n=== Post-Reset Verification ===")
        print(f"  Materials:           {mat_count} (Expected 0)")
        print(f"  CNMC Codes:          {cnmc_count} (Expected 0)")
        print(f"  Review Queue Items:  {rev_count} (Expected 0)")
        print(f"  Ingestion Batches:   {batch_count} (Expected 0)")
        print(f"  Reference CPSEs:     {cpse_count} (Preserved)")
        print(f"  Users:               {user_count} (Preserved)")
        print(f"  Taxonomies:          {tax_count} (Preserved)")

if __name__ == "__main__":
    reset_all_data()
