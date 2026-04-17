import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PairwiseComparison(Base):
    """Interleaved pairwise preference trial: (x, y_A, y_B) with optional user choice."""

    __tablename__ = "pairwise_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_a_version: Mapped[str] = mapped_column(String(160), nullable=False)
    model_b_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prediction_a: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prediction_b: Mapped[dict] = mapped_column(JSONB, nullable=False)
    left_is_model_a: Mapped[bool] = mapped_column(Boolean, nullable=False)
    chose_model_a: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
