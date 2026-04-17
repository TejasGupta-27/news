from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PairwiseOption(BaseModel):
    label: str
    label_id: int
    confidence: float
    probabilities: dict[str, float]


class PairwiseCreateRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)


class PairwiseCreateResponse(BaseModel):
    comparison_id: str
    left: PairwiseOption
    right: PairwiseOption


class PairwiseChoiceRequest(BaseModel):
    preferred_side: Literal["left", "right"]


class PairwiseChoiceResponse(BaseModel):
    ok: bool
    chose_model_a: bool
    already_recorded: bool = False


class TopicWinRate(BaseModel):
    topic: str
    n: int
    win_rate_a: float


class AbStatsResponse(BaseModel):
    total_comparisons: int
    completed: int
    wins_a: int
    wins_b: int
    win_rate_a: float | None
    wilson_low: float | None
    wilson_high: float | None
    decision: dict
    models: dict[str, str]
    topic_consistency: list[TopicWinRate]
    # Persisted routing snapshot (Beta prior + real pairwise labels only)
    ab_testing_enabled: bool
    p_use_model_a: float
    beta_alpha: int
    beta_beta: int
    routing_n_completed: int
    routing_wins_a: int
    routing_wins_b: int
    routing_updated_at: datetime | None


class AbSettingsPatch(BaseModel):
    ab_testing_enabled: bool


class AbSettingsResponse(BaseModel):
    ab_testing_enabled: bool
    p_use_model_a: float
    beta_alpha: int
    beta_beta: int
    n_completed_feedback: int
    wins_a: int
    wins_b: int
    updated_at: datetime | None


class PairwiseExportItem(BaseModel):
    id: UUID
    text: str
    model_a_version: str
    model_b_version: str
    prediction_a: dict
    prediction_b: dict
    left_is_model_a: bool
    chose_model_a: bool | None
    created_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}
