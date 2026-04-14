import uuid
from datetime import datetime

from sqlalchemy import Integer, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DriftReport(Base):
    __tablename__ = "drift_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    label_drift_pvalue: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence_drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reference_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False)
    current_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    triggered_retraining: Mapped[bool] = mapped_column(Boolean, default=False)
