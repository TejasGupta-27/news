from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.prediction import PredictionLog
from app.schemas.prediction import (
    PredictRequest,
    PredictResponse,
    PredictionListResponse,
    PredictionItem,
    CorrectRequest,
)
from app.services.classifier import classifier_service
from app.utils.cache import text_hash, get_cached_prediction, set_cached_prediction

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, db: AsyncSession = Depends(get_db)):
    hash_key = text_hash(req.text)

    if not req.explain:
        cached = await get_cached_prediction(hash_key)
        if cached:
            return PredictResponse(**cached)

    result = classifier_service.predict(req.text)

    explanation = None
    if req.explain:
        from app.services.explainer import explain_prediction
        explanation = explain_prediction(req.text, result["label_id"])

    response_data = {
        **result,
        "explanation": explanation,
        "model_version": classifier_service.model_version,
    }

    if not req.explain:
        await set_cached_prediction(hash_key, response_data)

    log = PredictionLog(
        text=req.text,
        text_hash=hash_key,
        predicted_label=result["label_id"],
        predicted_name=result["label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        explanation=explanation,
        model_version=classifier_service.model_version,
    )
    db.add(log)
    await db.commit()

    return PredictResponse(**response_data)


@router.get("/predictions", response_model=PredictionListResponse)
async def list_predictions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    label: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PredictionLog).order_by(PredictionLog.created_at.desc())
    count_query = select(func.count()).select_from(PredictionLog)

    if label:
        query = query.where(PredictionLog.predicted_name == label)
        count_query = count_query.where(PredictionLog.predicted_name == label)

    total = (await db.execute(count_query)).scalar()
    rows = (await db.execute(query.offset(offset).limit(limit))).scalars().all()

    return PredictionListResponse(
        items=[PredictionItem.model_validate(r) for r in rows],
        total=total,
    )


@router.patch("/predictions/{prediction_id}/correct")
async def correct_prediction(
    prediction_id: UUID,
    req: CorrectRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PredictionLog).where(PredictionLog.id == prediction_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prediction not found")

    log.corrected_label = req.corrected_label
    await db.commit()
    return {"ok": True}
