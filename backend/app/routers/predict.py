from uuid import UUID
import asyncio
import random

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
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
from app.services.ab_routing import ensure_routing_state
from app.services.classifier import ab_classifier_b, classifier_service
from app.utils.cache import text_hash, get_cached_prediction, set_cached_prediction
from app.utils.file_processor import extract_text_from_file, is_supported_file_format
from app.utils import metrics as m
import time

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, db: AsyncSession = Depends(get_db)):
    hash_key = text_hash(req.text)

    routing_state = await ensure_routing_state(db)
    routing_active = bool(routing_state.ab_testing_enabled)
    use_text_cache = not req.explain and not routing_active

    if use_text_cache:
        cached = await get_cached_prediction(hash_key)
        if cached:
            m.cache_hits.inc()
            return PredictResponse(**cached)
        m.cache_misses.inc()

    svc = classifier_service
    served = "a"
    if routing_active:
        p = min(1.0, max(0.0, float(routing_state.p_use_model_a)))
        if random.random() >= p:
            svc = ab_classifier_b
            served = "b"

    t0 = time.perf_counter()
    result = await asyncio.to_thread(svc.predict, req.text)
    model_version = svc.model_version
    m.prediction_latency.labels(model_version=model_version).observe(time.perf_counter() - t0)
    m.prediction_total.labels(label=result["label"], model_version=model_version).inc()
    m.prediction_confidence.labels(model_version=model_version).observe(result["confidence"])

    explanation = None
    if req.explain:
        try:
            from app.services.explainer import explain_prediction
            # Run explanation generation in thread to avoid blocking
            explanation = await asyncio.to_thread(
                explain_prediction, req.text, result["label_id"]
            )
        except Exception as e:
            print(f"Error generating explanation: {e}")
            # Continue without explanation on error
            explanation = None

    response_data = {
        **result,
        "explanation": explanation,
        "model_version": model_version,
        "ab_routing_enabled": routing_active,
        "ab_served_model": served,
    }

    if use_text_cache:
        await set_cached_prediction(hash_key, response_data)

    log = PredictionLog(
        text=req.text,
        text_hash=hash_key,
        predicted_label=result["label_id"],
        predicted_name=result["label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        explanation=explanation,
        model_version=model_version,
    )
    db.add(log)
    await db.commit()

    response_data["prediction_id"] = str(log.id)
    return PredictResponse(**response_data)


@router.post("/predict/file", response_model=PredictResponse)
async def predict_from_file(
    file: UploadFile = File(...),
    explain: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict from uploaded file (PDF, DOCX, or TXT).
    
    Supports:
    - .pdf: PDF documents
    - .docx: Microsoft Word documents
    - .txt: Plain text files
    """
    from fastapi import HTTPException
    
    # Validate file format
    if not is_supported_file_format(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: .txt, .pdf, .docx"
        )
    
    # Read and extract text from file
    try:
        file_content = await file.read()
        text = await asyncio.to_thread(
            extract_text_from_file,
            file_content,
            file.filename or "file"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")
    
    # Validate extracted text length
    if len(text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Extracted text must be at least 10 characters long"
        )
    
    # Use existing predict logic
    hash_key = text_hash(text)
    
    routing_state = await ensure_routing_state(db)
    routing_active = bool(routing_state.ab_testing_enabled)
    use_text_cache = not explain and not routing_active
    
    if use_text_cache:
        cached = await get_cached_prediction(hash_key)
        if cached:
            m.cache_hits.inc()
            return PredictResponse(**cached)
        m.cache_misses.inc()
    
    svc = classifier_service
    served = "a"
    if routing_active:
        p = min(1.0, max(0.0, float(routing_state.p_use_model_a)))
        if random.random() >= p:
            svc = ab_classifier_b
            served = "b"
    
    t0 = time.perf_counter()
    result = await asyncio.to_thread(svc.predict, text)
    model_version = svc.model_version
    m.prediction_latency.observe(time.perf_counter() - t0)
    m.prediction_total.labels(label=result["label"], model_version=model_version).inc()
    m.prediction_confidence.observe(result["confidence"])
    
    explanation = None
    if explain:
        try:
            from app.services.explainer import explain_prediction
            explanation = await asyncio.to_thread(
                explain_prediction, text, result["label_id"]
            )
        except Exception as e:
            print(f"Error generating explanation: {e}")
            explanation = None
    
    response_data = {
        **result,
        "explanation": explanation,
        "model_version": model_version,
        "ab_routing_enabled": routing_active,
        "ab_served_model": served,
    }
    
    if use_text_cache:
        await set_cached_prediction(hash_key, response_data)
    
    log = PredictionLog(
        text=text,
        text_hash=hash_key,
        predicted_label=result["label_id"],
        predicted_name=result["label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        explanation=explanation,
        model_version=model_version,
    )
    db.add(log)
    await db.commit()
    
    response_data["prediction_id"] = str(log.id)
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
