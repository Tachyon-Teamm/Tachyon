from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import SyncSessionLocal, sync_engine
from app.core.security import get_password_hash
from app.models.models import Base, CPSE, User, TaxonomyCategory
from app.db.seed_data import seed_enterprise_scenarios

def init_db():
    Base.metadata.create_all(bind=sync_engine)
    with sync_engine.connect() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON material_embeddings USING hnsw (embedding vector_cosine_ops);"))
            conn.commit()
        except Exception as e:
            print(f"[init_db] Note on index creation: {e}")
    db = SyncSessionLocal()
    try:
        # 1. Seed CPSEs
        cpses_data = [
            {"code": "CPCL", "name": "Chennai Petroleum Corporation Limited"},
            {"code": "IOCL", "name": "Indian Oil Corporation Limited"},
            {"code": "BPCL", "name": "Bharat Petroleum Corporation Limited"},
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

        # 4. Seed Synthetic Multi-CPSE Enterprise Datasets
        seed_enterprise_scenarios(db)

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
