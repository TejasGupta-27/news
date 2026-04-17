"""Pairwise A/B comparison logs

Revision ID: 002
Revises: 001
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pairwise_comparisons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("model_a_version", sa.String(160), nullable=False),
        sa.Column("model_b_version", sa.String(160), nullable=False),
        sa.Column("prediction_a", JSONB(), nullable=False),
        sa.Column("prediction_b", JSONB(), nullable=False),
        sa.Column("left_is_model_a", sa.Boolean(), nullable=False),
        sa.Column("chose_model_a", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_pairwise_created", "pairwise_comparisons", ["created_at"])
    op.create_index("idx_pairwise_hash", "pairwise_comparisons", ["text_hash"])


def downgrade() -> None:
    op.drop_table("pairwise_comparisons")
