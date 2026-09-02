import time
import pytest
from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db
from app.models.models import IngestionBatch, RawMaterial, Material, CPSE
from app.tasks.ingestion_tasks import process_ingestion_batch_task, mock_heavy_task

def test_chunk3_async_worker_non_blocking():
    t0 = time.time()
    future = mock_heavy_task.delay(0.2)
    elapsed = time.time() - t0
    
    # Assert non-blocking HTTP dispatch (< 50ms)
    assert elapsed < 0.05
    assert future is not None
    
    # Wait for result from worker thread
    res = future.get(timeout=10)
    assert res == "COMPLETED"

def test_chunk3_batch_processing_lifecycle():
    db = next(get_sync_db())
    try:
        cpse = db.query(CPSE).filter(CPSE.code == "IOCL").first()
        if not cpse:
            cpse = CPSE(code="IOCL", name="Indian Oil Corporation Ltd", sector="OIL_AND_GAS")
            db.add(cpse)
            db.commit()

        batch = IngestionBatch(
            cpse_id=cpse.id,
            file_name="test_chunk3.csv",
            total_rows=2,
            processed_rows=0,
            status="PENDING"
        )
        db.add(batch)
        db.commit()

        raw1 = RawMaterial(
            batch_id=batch.id,
            cpse_id=cpse.id,
            row_index=1,
            raw_data={"MATERIAL_NO": "CH3-001", "ITEM_SPEC": "VALVE GATE 2IN 300# FLG", "UOM": "EA", "PRICE": "4500", "VENDOR": "L&T"}
        )
        raw2 = RawMaterial(
            batch_id=batch.id,
            cpse_id=cpse.id,
            row_index=2,
            raw_data={"MATERIAL_NO": "CH3-002", "ITEM_SPEC": "PIPE CS 4IN SCH 40", "UOM": "MTR", "PRICE": "2100", "VENDOR": "Jindal"}
        )
        db.add_all([raw1, raw2])
        db.commit()

        mapping = {
            "material_code": "MATERIAL_NO",
            "short_description": "ITEM_SPEC",
            "uom": "UOM",
            "base_price": "PRICE",
            "vendor_name": "VENDOR"
        }

        # Dispatch async task
        t0 = time.time()
        fut = process_ingestion_batch_task.delay(batch.id, mapping)
        elapsed = time.time() - t0
        assert elapsed < 0.05 # Non-blocking dispatch!

        # Wait for worker completion
        fut.get(timeout=10)

        db.refresh(batch)
        assert batch.status == "COMPLETED"
        assert batch.processed_rows == 2

        # Verify Gold Layer entities created
        mats = db.query(Material).filter(Material.material_code.in_(["CH3-001", "CH3-002"])).all()
        assert len(mats) == 2
    finally:
        db.close()
