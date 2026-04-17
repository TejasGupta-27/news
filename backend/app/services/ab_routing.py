"""Persisted Beta–Bernoulli routing from real pairwise preferences (no synthetic labels)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_routing_state import ROUTING_STATE_ROW_ID, AbRoutingState
from app.models.pairwise import PairwiseComparison


async def get_routing_state(db: AsyncSession) -> AbRoutingState | None:
    r = await db.execute(select(AbRoutingState).where(AbRoutingState.id == ROUTING_STATE_ROW_ID))
    return r.scalar_one_or_none()


async def ensure_routing_state(db: AsyncSession) -> AbRoutingState:
    row = await get_routing_state(db)
    if row is not None:
        return row
    row = AbRoutingState(
        id=ROUTING_STATE_ROW_ID,
        ab_testing_enabled=True,
        beta_alpha=1,
        beta_beta=1,
        p_use_model_a=0.5,
        n_completed_feedback=0,
        wins_a=0,
        wins_b=0,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def refresh_routing_from_pairwise_feedback(db: AsyncSession) -> AbRoutingState:
    """
    Recompute Beta posterior from rows with real user labels (chose_model_a IS NOT NULL).
    Posterior mean p_use_model_a = alpha / (alpha + beta).
    """
    state = await ensure_routing_state(db)
    if not state.ab_testing_enabled:
        return state

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
    wins_b = int(completed) - int(wins_a)

    alpha = 1 + int(wins_a)
    beta = 1 + int(wins_b)
    p = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.5

    state.beta_alpha = alpha
    state.beta_beta = beta
    state.p_use_model_a = float(p)
    state.n_completed_feedback = int(completed)
    state.wins_a = int(wins_a)
    state.wins_b = int(wins_b)
    state.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(state)
    return state


async def set_ab_testing_enabled(db: AsyncSession, enabled: bool) -> AbRoutingState:
    state = await ensure_routing_state(db)
    state.ab_testing_enabled = enabled
    state.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(state)
    return state
