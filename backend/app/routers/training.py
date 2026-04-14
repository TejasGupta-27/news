from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.training_run import TrainingRun
from app.schemas.training import TrainingRunResponse, TrainingRunListResponse, TriggerResponse

router = APIRouter()


@router.get("/training/runs", response_model=TrainingRunListResponse)
async def list_training_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return TrainingRunListResponse(
        items=[TrainingRunResponse.model_validate(r) for r in runs]
    )


@router.get("/training/status", response_model=TrainingRunResponse | None)
async def get_training_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.status == "running")
        .order_by(TrainingRun.started_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        return None
    return TrainingRunResponse.model_validate(run)


@router.post("/training/trigger", response_model=TriggerResponse)
async def trigger_training():
    import asyncio
    from app.services.retrainer import trigger_retraining

    asyncio.create_task(trigger_retraining(None, "manual"))
    return TriggerResponse(message="Retraining triggered")
