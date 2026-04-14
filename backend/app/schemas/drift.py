from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DriftReportResponse(BaseModel):
    id: UUID
    check_time: datetime
    window_start: datetime
    window_end: datetime
    sample_count: int
    label_drift_pvalue: float | None
    label_drift_detected: bool
    confidence_drift_score: float | None
    confidence_drift_detected: bool
    reference_distribution: dict
    current_distribution: dict
    triggered_retraining: bool

    model_config = {"from_attributes": True}


class DriftHistoryResponse(BaseModel):
    items: list[DriftReportResponse]
