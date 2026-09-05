from typing import List
from fastapi import APIRouter
from app.core.database import get_sync_db
from app.schemas.schemas import DashboardSummaryResponse, DemandSavingsItem
from app.services.analytics.dashboard_service import DashboardService

router = APIRouter(prefix="/analytics", tags=["Executive Analytics Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    db = next(get_sync_db())
    try:
        return DashboardService.get_executive_summary(db)
    finally:
        db.close()

@router.get("/demand-savings", response_model=List[DemandSavingsItem])
def get_demand_savings():
    db = next(get_sync_db())
    try:
        return DashboardService.get_demand_aggregation_table(db)
    finally:
        db.close()

