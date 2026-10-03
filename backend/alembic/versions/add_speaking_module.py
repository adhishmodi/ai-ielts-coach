"""add speaking module

Revision ID: add_speaking_module
Revises: add_writing_module
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "add_speaking_module"
down_revision: Union[str, Sequence[str], None] = "add_writing_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "speaking_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_type", sa.String(length=30), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "speaking_parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("speaking_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("part_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("preparation_seconds", sa.Integer(), nullable=False),
        sa.Column("response_seconds", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["speaking_test_id"], ["speaking_tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("speaking_test_id", "part_number", name="uq_speaking_part_number"),
    )
    op.create_index("ix_speaking_parts_speaking_test_id", "speaking_parts", ["speaking_test_id"])
    op.create_table(
        "speaking_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("speaking_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("overall_band", sa.Numeric(2, 1), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaking_test_id"], ["speaking_tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speaking_attempts_user_id", "speaking_attempts", ["user_id"])
    op.create_index("ix_speaking_attempts_speaking_test_id", "speaking_attempts", ["speaking_test_id"])
    op.create_table(
        "speaking_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("part_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["speaking_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_id"], ["speaking_parts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "part_id", name="uq_speaking_response_part"),
    )
    op.create_index("ix_speaking_responses_attempt_id", "speaking_responses", ["attempt_id"])
    op.create_index("ix_speaking_responses_part_id", "speaking_responses", ["part_id"])
    op.create_table(
        "speaking_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fluency_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("lexical_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("grammar_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("pronunciation_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("overall_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(), nullable=True),
        sa.Column("improvements", postgresql.JSONB(), nullable=True),
        sa.Column("evaluated_by", sa.String(length=20), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["response_id"], ["speaking_responses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id"),
    )
    op.create_index("ix_speaking_evaluations_response_id", "speaking_evaluations", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_speaking_evaluations_response_id", table_name="speaking_evaluations")
    op.drop_table("speaking_evaluations")
    op.drop_index("ix_speaking_responses_part_id", table_name="speaking_responses")
    op.drop_index("ix_speaking_responses_attempt_id", table_name="speaking_responses")
    op.drop_table("speaking_responses")
    op.drop_index("ix_speaking_attempts_speaking_test_id", table_name="speaking_attempts")
    op.drop_index("ix_speaking_attempts_user_id", table_name="speaking_attempts")
    op.drop_table("speaking_attempts")
    op.drop_index("ix_speaking_parts_speaking_test_id", table_name="speaking_parts")
    op.drop_table("speaking_parts")
    op.drop_table("speaking_tests")
