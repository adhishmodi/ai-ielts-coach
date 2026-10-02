"""add writing module

Revision ID: add_writing_module
Revises: add_listening_module
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "add_writing_module"
down_revision: Union[str, Sequence[str], None] = "add_listening_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "writing_tests",
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
        "writing_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("writing_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_number", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("minimum_words", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["writing_test_id"], ["writing_tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("writing_test_id", "task_number", name="uq_writing_task_number"),
    )
    op.create_index("ix_writing_tasks_writing_test_id", "writing_tasks", ["writing_test_id"])

    op.create_table(
        "writing_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("writing_test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("overall_band", sa.Numeric(2, 1), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["writing_test_id"], ["writing_tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_writing_attempts_user_id", "writing_attempts", ["user_id"])
    op.create_index("ix_writing_attempts_writing_test_id", "writing_attempts", ["writing_test_id"])

    op.create_table(
        "writing_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["writing_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "task_id", name="uq_writing_submission_task"),
    )
    op.create_index("ix_writing_submissions_attempt_id", "writing_submissions", ["attempt_id"])
    op.create_index("ix_writing_submissions_task_id", "writing_submissions", ["task_id"])

    op.create_table(
        "writing_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_response_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("task_achievement_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("coherence_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("lexical_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("grammar_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("overall_band", sa.Numeric(2, 1), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(), nullable=True),
        sa.Column("improvements", postgresql.JSONB(), nullable=True),
        sa.Column("evaluated_by", sa.String(length=20), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["writing_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
    )
    op.create_index("ix_writing_evaluations_submission_id", "writing_evaluations", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_writing_evaluations_submission_id", table_name="writing_evaluations")
    op.drop_table("writing_evaluations")
    op.drop_index("ix_writing_submissions_task_id", table_name="writing_submissions")
    op.drop_index("ix_writing_submissions_attempt_id", table_name="writing_submissions")
    op.drop_table("writing_submissions")
    op.drop_index("ix_writing_attempts_writing_test_id", table_name="writing_attempts")
    op.drop_index("ix_writing_attempts_user_id", table_name="writing_attempts")
    op.drop_table("writing_attempts")
    op.drop_index("ix_writing_tasks_writing_test_id", table_name="writing_tasks")
    op.drop_table("writing_tasks")
    op.drop_table("writing_tests")
