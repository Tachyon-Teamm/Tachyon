from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db, get_sync_db
from app.core.security import get_current_user, TokenData
from app.models.models import MatchJob, MatchCandidate
from app.services.matching.matcher_engine import MatcherEngine

router = APIRouter(prefix="/matching", tags=["Matching Engine"])

@router.post("/trigger")
async def trigger_matching_job(
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
    
    # Run matching engine synchronously for fast feedback
    sync_db = next(get_sync_db())
    try:
        result = MatcherEngine.execute_cross_cpse_matching(sync_db, job.id)
    finally:
        sync_db.close()
        
    return {
        "job_id": job.id,
        "status": "COMPLETED",
        "result": result
    }

@router.get("/jobs")
async def list_match_jobs(db: Session = Depends(get_db)):
    res = await db.execute(select(MatchJob).order_by(MatchJob.started_at.desc()))
    jobs = res.scalars().all()
    return jobs
