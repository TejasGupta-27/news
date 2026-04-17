"""Singleton A/B routing state (learned from real pairwise feedback)

Revision ID: 003
Revises: 002
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ab_routing_state",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("ab_testing_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("beta_alpha", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("beta_beta", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("p_use_model_a", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("n_completed_feedback", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "INSERT INTO ab_routing_state (id) SELECT 1 WHERE NOT EXISTS "
        "(SELECT 1 FROM ab_routing_state WHERE id = 1)"
    )


def downgrade() -> None:
    op.drop_table("ab_routing_state")
