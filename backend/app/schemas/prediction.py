from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)
    explain: bool = False


class PredictResponse(BaseModel):
    label: str
    label_id: int
    confidence: float
    probabilities: dict[str, float]
    explanation: list[dict] | None = None
    model_version: str


class PredictionItem(BaseModel):
    id: UUID
    text: str
    predicted_name: str
    predicted_label: int
    confidence: float
    probabilities: dict[str, float]
    corrected_label: int | None
    model_version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    items: list[PredictionItem]
    total: int


class CorrectRequest(BaseModel):
    corrected_label: int = Field(..., ge=0, le=3)
