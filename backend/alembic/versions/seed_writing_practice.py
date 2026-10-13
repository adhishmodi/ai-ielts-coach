"""Seed an initial Academic IELTS Writing practice test.

The prompts are original practice material and do not reproduce an official IELTS test.
"""
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "seed_writing_practice"
down_revision: Union[str, Sequence[str], None] = "improve_listening_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEST_ID = UUID("c3300000-0000-4000-8000-000000000001")
TASK_1_ID = UUID("c3300000-0000-4000-8000-000000000011")
TASK_2_ID = UUID("c3300000-0000-4000-8000-000000000012")


def upgrade() -> None:
    bind = op.get_bind()
    tests = sa.table(
        "writing_tests",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("test_type", sa.String),
        sa.column("difficulty", sa.String),
        sa.column("time_limit_minutes", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    tasks = sa.table(
        "writing_tasks",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("writing_test_id", postgresql.UUID(as_uuid=True)),
        sa.column("task_number", sa.Integer),
        sa.column("task_type", sa.String),
        sa.column("prompt", sa.Text),
        sa.column("instructions", sa.Text),
        sa.column("minimum_words", sa.Integer),
        sa.column("order", sa.Integer),
    )

    if bind.execute(sa.select(tests.c.id).where(tests.c.id == TEST_ID)).first():
        return

    bind.execute(
        tests.insert().values(
            id=TEST_ID,
            title="Academic Writing Practice 1: Work and Transport",
            description=(
                "A two-task Academic IELTS Writing practice. Task 1 asks you to "
                "summarise a small data table; Task 2 asks for a balanced essay. "
                "This is original practice material, not an official IELTS paper."
            ),
            test_type="academic",
            difficulty="medium",
            time_limit_minutes=60,
            created_at=sa.func.now(),
        )
    )
    bind.execute(
        tasks.insert(),
        [
            {
                "id": TASK_1_ID,
                "writing_test_id": TEST_ID,
                "task_number": 1,
                "task_type": "graph",
                "prompt": (
                    "The table below shows the percentage of commuters using three "
                    "types of transport in a city in 2010 and 2025. Summarise the "
                    "information by selecting and reporting the main features, and "
                    "make comparisons where relevant.\n\n"
                    "Transport mode | 2010 | 2025\n"
                    "Private car | 62% | 48%\n"
                    "Public transport | 25% | 36%\n"
                    "Cycling or walking | 13% | 16%"
                ),
                "instructions": (
                    "Write at least 150 words. Include a clear overview, compare the "
                    "main changes, and support your summary with relevant figures. "
                    "Do not give personal opinions."
                ),
                "minimum_words": 150,
                "order": 1,
            },
            {
                "id": TASK_2_ID,
                "writing_test_id": TEST_ID,
                "task_number": 2,
                "task_type": "essay",
                "prompt": (
                    "Some people believe that working from home benefits both "
                    "employees and employers, while others think that working in an "
                    "office is more effective. Discuss both views and give your own opinion."
                ),
                "instructions": (
                    "Write at least 250 words. Discuss both perspectives, explain "
                    "your position, and support your ideas with reasons and examples. "
                    "Allow about 40 minutes for this task."
                ),
                "minimum_words": 250,
                "order": 2,
            },
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM writing_tasks WHERE id IN ("
            "'c3300000-0000-4000-8000-000000000011',"
            "'c3300000-0000-4000-8000-000000000012')"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM writing_tests WHERE id = "
            "'c3300000-0000-4000-8000-000000000001'"
        )
    )
