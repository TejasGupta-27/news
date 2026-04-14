import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mlflow_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    drift_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drift_reports.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_macro: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    deployed: Mapped[bool] = mapped_column(Boolean, default=False)
    model_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
