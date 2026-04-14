from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.drift_report import DriftReport
from app.schemas.drift import DriftReportResponse, DriftHistoryResponse

router = APIRouter()


@router.get("/drift/latest", response_model=DriftReportResponse | None)
async def get_latest_drift(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DriftReport).order_by(DriftReport.check_time.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return None
    return DriftReportResponse.model_validate(report)


@router.get("/drift/history", response_model=DriftHistoryResponse)
async def get_drift_history(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(DriftReport)
        .where(DriftReport.check_time >= since)
        .order_by(DriftReport.check_time.desc())
    )
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
