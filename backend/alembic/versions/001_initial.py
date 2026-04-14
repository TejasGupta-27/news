"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prediction_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("predicted_label", sa.SmallInteger(), nullable=False),
        sa.Column("predicted_name", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("probabilities", JSONB(), nullable=False),
        sa.Column("explanation", JSONB(), nullable=True),
        sa.Column("corrected_label", sa.SmallInteger(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_predictions_created", "prediction_logs", ["created_at"])
    op.create_index("idx_predictions_label", "prediction_logs", ["predicted_label"])
    op.create_index("idx_predictions_hash", "prediction_logs", ["text_hash"])

    op.create_table(
        "drift_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("check_time", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("label_drift_pvalue", sa.Float(), nullable=True),
        sa.Column("label_drift_detected", sa.Boolean(), nullable=False),
        sa.Column("confidence_drift_score", sa.Float(), nullable=True),
        sa.Column("confidence_drift_detected", sa.Boolean(), nullable=False),
        sa.Column("reference_distribution", JSONB(), nullable=False),
        sa.Column("current_distribution", JSONB(), nullable=False),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("triggered_retraining", sa.Boolean(), server_default=sa.text("false")),
    )
    op.create_index("idx_drift_time", "drift_reports", ["check_time"])

    op.create_table(
        "training_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mlflow_run_id", sa.String(64), nullable=False),
        sa.Column("trigger_reason", sa.String(50), nullable=False),
        sa.Column("drift_report_id", UUID(as_uuid=True), sa.ForeignKey("drift_reports.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("f1_macro", sa.Float(), nullable=True),
        sa.Column("previous_f1", sa.Float(), nullable=True),
        sa.Column("deployed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("model_uri", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("idx_training_status", "training_runs", ["status"])


def downgrade() -> None:
    op.drop_table("training_runs")
    op.drop_table("drift_reports")
    op.drop_table("prediction_logs")
