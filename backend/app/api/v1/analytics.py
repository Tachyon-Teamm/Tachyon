from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_sync_db
from app.schemas.schemas import (
    DashboardSummaryResponse, DemandSavingsItem, QualityHeatmapItem, VennOverlapData
)
from app.services.analytics.dashboard_service import DashboardService

router = APIRouter(prefix="/analytics", tags=["Executive Analytics Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary():
    db = next(get_sync_db())
    try:
        return DashboardService.get_executive_summary(db)
    finally:
        db.close()

@router.get("/demand-savings", response_model=List[DemandSavingsItem])
async def get_demand_savings():
    db = next(get_sync_db())
    try:
        return DashboardService.get_demand_aggregation_table(db)
    finally:
        db.close()

@router.get("/quality-heatmap", response_model=List[QualityHeatmapItem])
async def get_quality_heatmap():
    db = next(get_sync_db())
    try:
        return DashboardService.get_data_quality_heatmap(db)
    finally:
        db.close()

@router.get("/venn-overlap", response_model=VennOverlapData)
async def get_venn_overlap():
    db = next(get_sync_db())
    try:
        return DashboardService.get_venn_overlap(db)
    finally:
        db.close()
