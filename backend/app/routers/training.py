import os
import sys
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.training_run import TrainingRun
from app.schemas.training import TrainingRunResponse, TrainingRunListResponse, TriggerResponse

router = APIRouter()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))


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


@router.get("/model/versions")
async def list_versions():
    from ml.pipeline.registry import list_model_versions
    try:
        return {"items": list_model_versions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MLflow error: {e}")


@router.post("/model/rollback/{version}")
async def rollback_model(version: str):
    from ml.pipeline.registry import (
        promote_version_to_production,
        download_version_artifacts,
    )
    from app.config import settings
    from app.utils.storage import upload_directory
    from app.services.classifier import classifier_service
    from app.utils.cache import flush_prediction_cache

    try:
        promoted = promote_version_to_production(version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Version {version} not found: {e}")

    try:
        tmp = tempfile.mkdtemp()
        local_model_dir = download_version_artifacts(version, tmp)
        nested = os.path.join(local_model_dir, "model")
        if os.path.isdir(nested):
            local_model_dir = nested
        upload_directory(local_model_dir, settings.minio_bucket, "production/model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Artifact restore failed: {e}")

    try:
        from ml.pipeline import hf_hub
        if hf_hub.is_enabled():
            hf_hub.push_model(
                local_model_dir,
                mlflow_run_id=promoted["run_id"],
                metrics={"rollback_to_version": float(version)},
            )
    except Exception as e:
        print(f"HF rollback push failed (non-fatal): {e}")

    await classifier_service.reload()
    await flush_prediction_cache()

    return {
        "rolled_back_to": promoted,
        "model_version": classifier_service.model_version,
    }
