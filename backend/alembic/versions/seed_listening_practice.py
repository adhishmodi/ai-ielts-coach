"""Seed a starter IELTS-style Listening practice test.

The audio recordings are public learning resources from the U.S. Department of State's
American English program. The question set is original practice material.
"""
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "seed_listening_practice"
down_revision: Union[str, Sequence[str], None] = "add_listening_section_audio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEST_ID = UUID("b2200000-0000-4000-8000-000000000001")
SECTION_1_ID = UUID("b2200000-0000-4000-8000-000000000011")
SECTION_2_ID = UUID("b2200000-0000-4000-8000-000000000012")


def upgrade() -> None:
    bind = op.get_bind()
    tests = sa.table(
        "listening_tests",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("difficulty", sa.String),
        sa.column("time_limit_minutes", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    sections = sa.table(
        "listening_sections",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("listening_test_id", postgresql.UUID(as_uuid=True)),
        sa.column("title", sa.String),
        sa.column("instructions", sa.Text),
        sa.column("audio_url", sa.String),
        sa.column("order", sa.Integer),
    )
    questions = sa.table(
        "listening_questions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("section_id", postgresql.UUID(as_uuid=True)),
        sa.column("question_text", sa.Text),
        sa.column("question_type", sa.String),
        sa.column("options", sa.JSON),
        sa.column("correct_answer", sa.Text),
        sa.column("explanation", sa.Text),
        sa.column("order", sa.Integer),
    )

    # A fixed ID makes the seed deterministic and safe to inspect.
    exists = bind.execute(
        sa.select(tests.c.id).where(tests.c.id == TEST_ID)
    ).first()
    if exists:
        return

    bind.execute(
        tests.insert().values(
            id=TEST_ID,
            title="Listening Practice 1: Everyday Conversations",
            description=(
                "A starter listening practice using short everyday conversations. "
                "Listen for key details, then answer the questions. Audio is hosted "
                "by the U.S. Department of State's American English learning resource."
            ),
            difficulty="easy",
            time_limit_minutes=15,
            created_at=sa.func.now(),
        )
    )
    bind.execute(
        sections.insert(),
        [
            {
                "id": SECTION_1_ID,
                "listening_test_id": TEST_ID,
                "title": "Section 1: Ordering a Meal",
                "instructions": "Listen to the conversation and answer the questions. You may replay the audio while practising.",
                "audio_url": "https://americanenglish.state.gov/files/ae/resource_files/dialogue_2-01_ordering_a_meal.mp3",
                "order": 1,
            },
            {
                "id": SECTION_2_ID,
                "listening_test_id": TEST_ID,
                "title": "Section 2: Transportation",
                "instructions": "Listen to the conversation and answer the questions. Focus on the travel details mentioned.",
                "audio_url": "https://americanenglish.state.gov/files/ae/resource_files/dialogue_2-10_transportation.mp3",
                "order": 2,
            },
        ],
    )
    bind.execute(
        questions.insert(),
        [
            {
                "id": UUID("b2200000-0000-4000-8000-000000000101"),
                "section_id": SECTION_1_ID,
                "question_text": "What kind of situation is the first recording about?",
                "question_type": "multiple_choice",
                "options": ["Ordering food", "Booking a hotel", "Buying a train ticket", "Making a doctor's appointment"],
                "correct_answer": "Ordering food",
                "explanation": "The recording is titled 'Ordering a Meal' and presents a restaurant ordering conversation.",
                "order": 1,
            },
            {
                "id": UUID("b2200000-0000-4000-8000-000000000102"),
                "section_id": SECTION_1_ID,
                "question_text": "Where does the conversation most likely take place?",
                "question_type": "multiple_choice",
                "options": ["At a restaurant", "At a railway station", "At a university library", "At a pharmacy"],
                "correct_answer": "At a restaurant",
                "explanation": "The dialogue is a meal-ordering conversation.",
                "order": 2,
            },
            {
                "id": UUID("b2200000-0000-4000-8000-000000000103"),
                "section_id": SECTION_1_ID,
                "question_text": "Which skill is most useful for this recording?",
                "question_type": "multiple_choice",
                "options": ["Identifying food and order details", "Following a lecture on biology", "Understanding a weather forecast", "Describing a map route"],
                "correct_answer": "Identifying food and order details",
                "explanation": "A restaurant ordering dialogue requires listening for the food and order details.",
                "order": 3,
            },
            {
                "id": UUID("b2200000-0000-4000-8000-000000000201"),
                "section_id": SECTION_2_ID,
                "question_text": "What is the main topic of the second recording?",
                "question_type": "multiple_choice",
                "options": ["Transportation", "A job interview", "A family celebration", "A science experiment"],
                "correct_answer": "Transportation",
                "explanation": "The recording is titled 'Transportation'.",
                "order": 1,
            },
            {
                "id": UUID("b2200000-0000-4000-8000-000000000202"),
                "section_id": SECTION_2_ID,
                "question_text": "Which type of information should you listen for most carefully in a transportation conversation?",
                "question_type": "multiple_choice",
                "options": ["Travel arrangements and journey details", "Ingredients in a recipe", "Names of musical instruments", "Instructions for a laboratory test"],
                "correct_answer": "Travel arrangements and journey details",
                "explanation": "Transportation conversations commonly focus on how people travel and the details of a journey.",
                "order": 2,
            },
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Only remove rows belonging to this migration's deterministic seed IDs.
    bind.execute(
        sa.text(
            "DELETE FROM listening_questions WHERE id IN ("
            "'b2200000-0000-4000-8000-000000000101',"
            "'b2200000-0000-4000-8000-000000000102',"
            "'b2200000-0000-4000-8000-000000000103',"
            "'b2200000-0000-4000-8000-000000000201',"
            "'b2200000-0000-4000-8000-000000000202')"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM listening_sections WHERE id IN "
            "('b2200000-0000-4000-8000-000000000011', "
            "'b2200000-0000-4000-8000-000000000012')"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM listening_tests WHERE id = "
            "'b2200000-0000-4000-8000-000000000001'"
        )
    )
