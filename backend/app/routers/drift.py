from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.drift_report import DriftReport
from app.schemas.drift import DriftReportResponse, DriftHistoryResponse

router = APIRouter()


@router.get("/drift/latest", response_model=DriftReportResponse | None)
async def get_latest_drift(
    model_version: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get latest drift report, optionally filtered by model version."""
    query = select(DriftReport).order_by(DriftReport.check_time.desc())
    if model_version:
        query = query.where(DriftReport.model_version == model_version)
    query = query.limit(1)
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if not report:
        return None
    return DriftReportResponse.model_validate(report)


@router.get("/drift/latest-by-model", response_model=dict[str, DriftReportResponse | None])
async def get_latest_drift_by_model(db: AsyncSession = Depends(get_db)):
    """Get latest drift report for each model version."""
    result = await db.execute(
        select(DriftReport)
        .order_by(DriftReport.check_time.desc())
    )
    reports = result.scalars().all()
    
    latest_by_model = {}
    for report in reports:
        model_v = report.model_version or "unknown"
        if model_v not in latest_by_model:
            latest_by_model[model_v] = DriftReportResponse.model_validate(report)
    
    return latest_by_model


@router.get("/drift/history", response_model=DriftHistoryResponse)
async def get_drift_history(
    days: int = Query(7, ge=1, le=90),
    model_version: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get drift history, optionally filtered by model version."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = select(DriftReport).where(DriftReport.check_time >= since)
    
    if model_version:
        query = query.where(DriftReport.model_version == model_version)
    
    query = query.order_by(DriftReport.check_time.desc())
    result = await db.execute(query)
    reports = result.scalars().all()
    return DriftHistoryResponse(
        items=[DriftReportResponse.model_validate(r) for r in reports]
    )


@router.post("/drift/check", response_model=DriftReportResponse | None)
async def trigger_drift_check():
    from app.workers.drift_worker import run_drift_check
    report = await run_drift_check()
    if report:
        return DriftReportResponse.model_validate(report)
    return None
