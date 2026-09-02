from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import SyncSessionLocal, sync_engine
from app.core.security import get_password_hash
from app.models.models import Base, CPSE, User, TaxonomyCategory
from app.db.seed_data import seed_enterprise_scenarios
from app.db.taxonomy_seed import seed_multi_sector_taxonomies


def init_db():
    Base.metadata.create_all(bind=sync_engine)
    try:
        with sync_engine.begin() as conn:
            conn.execute(text("ALTER TABLE material_embeddings ADD COLUMN IF NOT EXISTS sparse_vector JSON DEFAULT '{}'::json"))
            conn.execute(text("ALTER TABLE material_embeddings ADD COLUMN IF NOT EXISTS model_name VARCHAR(50) DEFAULT 'all-MiniLM-L6-v2'"))
            conn.execute(text("ALTER TABLE match_candidates ADD COLUMN IF NOT EXISTS suggested_route VARCHAR(30) DEFAULT 'IDENTICAL'"))
            conn.execute(text("ALTER TABLE match_jobs ADD COLUMN IF NOT EXISTS error_message TEXT"))
            conn.execute(text("ALTER TABLE match_jobs ALTER COLUMN error_message TYPE TEXT"))
            conn.execute(text("ALTER TABLE ingestion_batches ADD COLUMN IF NOT EXISTS error_message TEXT"))
            conn.execute(text("ALTER TABLE ingestion_batches ADD COLUMN IF NOT EXISTS quality_score FLOAT"))
    except Exception as e:
        print(f"[init_db] Column safeguard notice: {e}")
    with sync_engine.connect() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON material_embeddings USING hnsw (embedding vector_cosine_ops);"))
            conn.commit()
        except Exception as e:
            print(f"[init_db] Note on index creation: {e}")
    db = SyncSessionLocal()
    try:
        # 1. Seed CPSEs across multi-sector landscape
        cpses_data = [
            {"code": "CPCL", "name": "Chennai Petroleum Corporation Limited", "sector": "OIL_AND_GAS"},
            {"code": "IOCL", "name": "Indian Oil Corporation Limited", "sector": "OIL_AND_GAS"},
            {"code": "BPCL", "name": "Bharat Petroleum Corporation Limited", "sector": "OIL_AND_GAS"},
            {"code": "ONGC", "name": "Oil and Natural Gas Corporation", "sector": "OIL_AND_GAS"},
            {"code": "NTPC", "name": "NTPC Limited (Power)", "sector": "POWER"},
            {"code": "SAIL", "name": "Steel Authority of India Limited", "sector": "STEEL"},
            {"code": "COALINDIA", "name": "Coal India Limited", "sector": "MINING"},
            {"code": "BHEL", "name": "Bharat Heavy Electricals Limited", "sector": "HEAVY_ENG"},
        ]
        
        for c_data in cpses_data:
            existing = db.query(CPSE).filter(CPSE.code == c_data["code"]).first()
            if not existing:
                db.add(CPSE(**c_data))
        db.commit()

        # 2. Seed Default Users with RBAC Roles
        users_data = [
            {"username": "admin", "email": "admin@unimm.gov.in", "role": "admin", "cpse_id": None},
            {"username": "steward", "email": "steward@iocl.co.in", "role": "data_steward", "cpse_id": 2},
            {"username": "reviewer", "email": "reviewer@cpcl.co.in", "role": "reviewer", "cpse_id": 1},
            {"username": "viewer", "email": "viewer@bpcl.in", "role": "viewer", "cpse_id": 3},
        ]
        
        for u_data in users_data:
            existing = db.query(User).filter(User.username == u_data["username"]).first()
            if not existing:
                u_obj = User(
                    username=u_data["username"],
                    email=u_data["email"],
                    hashed_password=get_password_hash("password"),
                    role=u_data["role"],
                    cpse_id=u_data["cpse_id"]
                )
                db.add(u_obj)
        db.commit()

        # 3. Seed UNSPSC Taxonomy Categories
        categories = [
            {"unspsc_code": "401416", "name": "Valves & Flow Control", "level": 1},
            {"unspsc_code": "401715", "name": "Industrial Pipes & Tubing", "level": 1},
            {"unspsc_code": "311715", "name": "Bearings & Bushings", "level": 1},
            {"unspsc_code": "312015", "name": "Gaskets & Seals", "level": 1},
            {"unspsc_code": "151215", "name": "Lubricants, Oils & Greases", "level": 1},
        ]
        
        for cat in categories:
            existing = db.query(TaxonomyCategory).filter(TaxonomyCategory.unspsc_code == cat["unspsc_code"]).first()
            if not existing:
                db.add(TaxonomyCategory(**cat))
        db.commit()

        # 4. Seed Multi-Sector eCl@ss 14.0 Hierarchical Taxonomy & Dynamic Invariant Dictionaries
        seed_multi_sector_taxonomies(db)

        # 5. Seed Synthetic Multi-CPSE Enterprise Datasets
        seed_enterprise_scenarios(db)

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
