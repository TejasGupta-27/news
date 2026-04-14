from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TrainingRunResponse(BaseModel):
    id: UUID
    mlflow_run_id: str
    trigger_reason: str
    status: str
    accuracy: float | None
    f1_macro: float | None
    previous_f1: float | None
    deployed: bool
    model_uri: str | None
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class TrainingRunListResponse(BaseModel):
    items: list[TrainingRunResponse]


class TriggerResponse(BaseModel):
    message: str
    run_id: UUID | None = None
