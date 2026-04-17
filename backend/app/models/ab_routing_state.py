from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Single-row table: id must always be 1.
ROUTING_STATE_ROW_ID = 1


class AbRoutingState(Base):
    __tablename__ = "ab_routing_state"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=ROUTING_STATE_ROW_ID)
    ab_testing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Beta(1,1) prior + counts from real pairwise feedback (chose_model_a) only
    beta_alpha: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    beta_beta: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    p_use_model_a: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    n_completed_feedback: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins_a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins_b: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
