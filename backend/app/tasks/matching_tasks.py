from typing import Optional
from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db
from app.services.matching.matcher_engine import MatcherEngine

@celery_app.task(name="execute_matching_job_task")
def execute_matching_job_task(job_id: int, scope: str = "ALL", target_cpse_id: Optional[int] = None):
    db = next(get_sync_db())
    try:
        result = MatcherEngine.execute_cross_cpse_matching(db, job_id, scope=scope, target_cpse_id=target_cpse_id)
        return result
    finally:
        db.close()
