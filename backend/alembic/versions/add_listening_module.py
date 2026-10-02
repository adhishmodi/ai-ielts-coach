"""add listening module

Revision ID: add_listening_module
Revises: 33630ac8143f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_listening_module"
down_revision: Union[str, Sequence[str], None] = "33630ac8143f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listening_tests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "listening_sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listening_test_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["listening_test_id"],
            ["listening_tests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listening_sections_listening_test_id",
        "listening_sections",
        ["listening_test_id"],
        unique=False,
    )
    op.create_table(
        "listening_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["listening_sections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listening_questions_section_id",
        "listening_questions",
        ["section_id"],
        unique=False,
    )
    op.create_table(
        "listening_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("listening_test_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("band_score", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.ForeignKeyConstraint(
            ["listening_test_id"],
            ["listening_tests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listening_attempts_listening_test_id",
        "listening_attempts",
        ["listening_test_id"],
        unique=False,
    )
    op.create_index(
        "ix_listening_attempts_user_id",
        "listening_attempts",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "listening_answers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["listening_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["listening_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listening_answers_attempt_id",
        "listening_answers",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        "ix_listening_answers_question_id",
        "listening_answers",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_listening_answers_question_id", table_name="listening_answers")
    op.drop_index("ix_listening_answers_attempt_id", table_name="listening_answers")
    op.drop_table("listening_answers")
    op.drop_index("ix_listening_attempts_user_id", table_name="listening_attempts")
    op.drop_index("ix_listening_attempts_listening_test_id", table_name="listening_attempts")
    op.drop_table("listening_attempts")
    op.drop_index("ix_listening_questions_section_id", table_name="listening_questions")
    op.drop_table("listening_questions")
    op.drop_index("ix_listening_sections_listening_test_id", table_name="listening_sections")
    op.drop_table("listening_sections")
    op.drop_table("listening_tests")
