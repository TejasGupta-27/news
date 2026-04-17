from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.pairwise import PairwiseComparison
from app.schemas.ab_testing import (
    AbSettingsPatch,
    AbSettingsResponse,
    AbStatsResponse,
    PairwiseChoiceRequest,
    PairwiseChoiceResponse,
    PairwiseCreateRequest,
    PairwiseCreateResponse,
    PairwiseExportItem,
    PairwiseOption,
    TopicWinRate,
)
from app.services.ab_routing import (
    ensure_routing_state,
    get_routing_state,
    refresh_routing_from_pairwise_feedback,
    set_ab_testing_enabled,
)
from app.services.classifier import ab_classifier_b, classifier_service
from app.utils.cache import text_hash
from app.utils.stats import preference_decision

router = APIRouter()


def _public_option(pred: dict) -> PairwiseOption:
    return PairwiseOption(
        label=pred["label"],
        label_id=int(pred["label_id"]),
        confidence=float(pred["confidence"]),
        probabilities={k: float(v) for k, v in pred["probabilities"].items()},
    )


@router.post("/ab/pairwise", response_model=PairwiseCreateResponse)
async def create_pairwise_comparison(req: PairwiseCreateRequest, db: AsyncSession = Depends(get_db)):
    state = await ensure_routing_state(db)
    if not state.ab_testing_enabled:
        raise HTTPException(
            status_code=403,
            detail="A/B collection is paused. Enable A/B testing in settings to run pairwise comparisons.",
        )

    text = req.text.strip()
    pred_a, pred_b = await asyncio.gather(
        asyncio.to_thread(classifier_service.predict, text),
        asyncio.to_thread(ab_classifier_b.predict, text),
    )
    left_is_model_a = secrets.randbelow(2) == 0
    if left_is_model_a:
        left, right = pred_a, pred_b
    else:
        left, right = pred_b, pred_a

    row = PairwiseComparison(
        text=text,
        text_hash=text_hash(text),
        model_a_version=classifier_service.model_version,
        model_b_version=ab_classifier_b.model_version,
        prediction_a=pred_a,
        prediction_b=pred_b,
        left_is_model_a=left_is_model_a,
        chose_model_a=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return PairwiseCreateResponse(
        comparison_id=str(row.id),
        left=_public_option(left),
        right=_public_option(right),
    )


@router.post("/ab/pairwise/{comparison_id}/choice", response_model=PairwiseChoiceResponse)
async def submit_pairwise_choice(
    comparison_id: UUID,
    req: PairwiseChoiceRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PairwiseComparison).where(PairwiseComparison.id == comparison_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if row.chose_model_a is not None:
        return PairwiseChoiceResponse(
            ok=True,
            chose_model_a=row.chose_model_a,
            already_recorded=True,
        )

    if req.preferred_side == "left":
        chose_a = row.left_is_model_a
    else:
        chose_a = not row.left_is_model_a

    row.chose_model_a = chose_a
    row.decided_at = datetime.now(timezone.utc)
    await db.commit()

    st = await get_routing_state(db)
    if st is not None and st.ab_testing_enabled:
        await refresh_routing_from_pairwise_feedback(db)

    return PairwiseChoiceResponse(ok=True, chose_model_a=chose_a, already_recorded=False)


@router.get("/ab/stats", response_model=AbStatsResponse)
async def ab_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(PairwiseComparison))).scalar() or 0
    completed = (
        await db.execute(
            select(func.count()).select_from(PairwiseComparison).where(PairwiseComparison.chose_model_a.is_not(None))
        )
    ).scalar() or 0
    wins_a = (
        await db.execute(
            select(func.count())
            .select_from(PairwiseComparison)
            .where(PairwiseComparison.chose_model_a.is_(True))
        )
    ).scalar() or 0
    wins_b = completed - wins_a

    win_rate = wins_a / completed if completed else None
    decision = preference_decision(wins_a, completed, epsilon=settings.ab_decision_epsilon)
    wilson_low = decision["wilson_low"]
    wilson_high = decision["wilson_high"]

    topic_consistency: list[TopicWinRate] = []
    topic_expr = PairwiseComparison.prediction_a["label"].astext
    wr_expr = func.avg(case((PairwiseComparison.chose_model_a.is_(True), 1.0), else_=0.0))
    stmt_topics = (
        select(topic_expr.label("topic"), func.count().label("n"), wr_expr.label("win_rate_a"))
        .where(PairwiseComparison.chose_model_a.is_not(None))
        .group_by(topic_expr)
    )
    trows = (await db.execute(stmt_topics)).all()
    for t, n, wr in trows:
        if t is None:
            continue
        topic_consistency.append(
            TopicWinRate(topic=str(t), n=int(n), win_rate_a=float(wr or 0.0))
        )

    st = await ensure_routing_state(db)

    return AbStatsResponse(
        total_comparisons=int(total),
        completed=int(completed),
        wins_a=int(wins_a),
        wins_b=int(wins_b),
        win_rate_a=win_rate,
        wilson_low=wilson_low,
        wilson_high=wilson_high,
        decision=decision,
        models={"a": classifier_service.model_version, "b": ab_classifier_b.model_version},
        topic_consistency=sorted(topic_consistency, key=lambda x: -x.n),
        ab_testing_enabled=st.ab_testing_enabled,
        p_use_model_a=float(st.p_use_model_a),
        beta_alpha=int(st.beta_alpha),
        beta_beta=int(st.beta_beta),
        routing_n_completed=int(st.n_completed_feedback),
        routing_wins_a=int(st.wins_a),
        routing_wins_b=int(st.wins_b),
        routing_updated_at=st.updated_at,
    )


@router.get("/ab/settings", response_model=AbSettingsResponse)
async def get_ab_settings(db: AsyncSession = Depends(get_db)):
    st = await ensure_routing_state(db)
    return AbSettingsResponse(
        ab_testing_enabled=st.ab_testing_enabled,
        p_use_model_a=float(st.p_use_model_a),
        beta_alpha=int(st.beta_alpha),
        beta_beta=int(st.beta_beta),
        n_completed_feedback=int(st.n_completed_feedback),
        wins_a=int(st.wins_a),
        wins_b=int(st.wins_b),
        updated_at=st.updated_at,
    )


@router.patch("/ab/settings", response_model=AbSettingsResponse)
async def patch_ab_settings(req: AbSettingsPatch, db: AsyncSession = Depends(get_db)):
    st = await set_ab_testing_enabled(db, req.ab_testing_enabled)
    if st.ab_testing_enabled:
        await refresh_routing_from_pairwise_feedback(db)
    return AbSettingsResponse(
        ab_testing_enabled=st.ab_testing_enabled,
        p_use_model_a=float(st.p_use_model_a),
        beta_alpha=int(st.beta_alpha),
        beta_beta=int(st.beta_beta),
        n_completed_feedback=int(st.n_completed_feedback),
        wins_a=int(st.wins_a),
        wins_b=int(st.wins_b),
        updated_at=st.updated_at,
    )


@router.get("/ab/export", response_model=list[PairwiseExportItem])
async def export_pairwise(
    limit: int = Query(500, ge=1, le=5000),
    completed_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    q = select(PairwiseComparison).order_by(PairwiseComparison.created_at.desc()).limit(limit)
    if completed_only:
        q = q.where(PairwiseComparison.chose_model_a.is_not(None))
    rows = (await db.execute(q)).scalars().all()
    return [PairwiseExportItem.model_validate(r) for r in rows]
