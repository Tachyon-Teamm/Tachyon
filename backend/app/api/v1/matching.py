from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db, get_sync_db
from app.core.security import get_current_user, TokenData
from app.models.models import MatchJob, MatchCandidate
from app.services.matching.matcher_engine import MatcherEngine
from app.tasks.matching_tasks import execute_matching_job_task

router = APIRouter(prefix="/matching", tags=["Matching Engine"])

class IncrementalMatchRequest(BaseModel):
    new_material_ids: List[int]

@router.post("/trigger")
async def trigger_matching_job(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    job = MatchJob(
        status="PENDING",
        parameters={"weights": {"semantic": 0.40, "attribute": 0.35, "procurement": 0.25}}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Asynchronous non-blocking dispatch with graceful Celery -> BackgroundTasks fallback
    try:
        execute_matching_job_task.delay(job.id)
    except Exception as celery_err:
        print(f"[Matching] Celery dispatch unavailable ({celery_err}), using FastAPI BackgroundTasks")
        background_tasks.add_task(execute_matching_job_task, job.id)
        
    return {
        "job_id": job.id,
        "status": "PROCESSING",
        "message": "Cross-CPSE matching job dispatched asynchronously"
    }

@router.post("/incremental")
async def trigger_incremental_matching(
    req: IncrementalMatchRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    job = MatchJob(
        status="PENDING",
        parameters={"mode": "INCREMENTAL", "count": len(req.new_material_ids)}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    sync_db = next(get_sync_db())
    try:
        res = MatcherEngine.execute_incremental_matching(sync_db, req.new_material_ids, job.id)
    finally:
        sync_db.close()

    return {
        "job_id": job.id,
        "status": "COMPLETED",
        "result": res
    }

@router.get("/jobs")
async def list_match_jobs(db: Session = Depends(get_db)):
    res = await db.execute(select(MatchJob).order_by(MatchJob.started_at.desc()))
    jobs = res.scalars().all()
    return jobs

@router.get("/jobs/{job_id}")
async def get_match_job_detail(job_id: int, db: Session = Depends(get_db)):
    res = await db.execute(select(MatchJob).filter(MatchJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

