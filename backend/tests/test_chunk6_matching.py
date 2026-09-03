import time
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.database import get_sync_db
from app.models.models import Material, CPSE, MatchJob

def test_chunk6_async_matching_trigger():
    client = TestClient(app)
    t0 = time.time()
    res = client.post("/api/v1/matching/trigger")
    elapsed = time.time() - t0
    
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "PROCESSING"
    # Verify non-blocking response time (< 200ms)
    assert elapsed < 0.2

    # Poll status
    job_id = data["job_id"]
    job_res = client.get(f"/api/v1/matching/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["id"] == job_id

def test_chunk6_incremental_matching_endpoint():
    client = TestClient(app)
    db = next(get_sync_db())
    try:
        mats = db.query(Material).limit(2).all()
        mat_ids = [m.id for m in mats] if mats else []
        
        req = {"new_material_ids": mat_ids}
        res = client.post("/api/v1/matching/incremental", json=req)
        assert res.status_code == 200
        data = res.json()
        assert "job_id" in data
        assert data["status"] == "COMPLETED"
    finally:
        db.close()
