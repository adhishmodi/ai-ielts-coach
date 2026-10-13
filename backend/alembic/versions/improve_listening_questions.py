"""Replace topic-obvious listening prompts with transcript-detail questions.

The seeded questions are based on the matching public audio dialogue transcripts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "improve_listening_questions"
down_revision: Union[str, Sequence[str], None] = "seed_listening_practice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

QUESTION_UPDATES = [
    (
        "b2200000-0000-4000-8000-000000000101",
        "What drink does Ralph order?",
        ["Iced tea", "Lemonade", "Coffee", "Orange juice"],
        "Iced tea",
        "Ralph says, “I'll have iced tea, please.”",
        1,
    ),
    (
        "b2200000-0000-4000-8000-000000000102",
        "How does Ralph want his roast beef cooked?",
        ["Rare", "Medium", "Well done", "He does not specify"],
        "Well done",
        "When asked how he wants the beef, Ralph replies, “Well done, please.”",
        2,
    ),
    (
        "b2200000-0000-4000-8000-000000000103",
        "Which main course does Anna choose?",
        ["Roast beef with peas", "Fish with potatoes and a salad", "Tomato soup only", "Chicken with rice"],
        "Fish with potatoes and a salad",
        "Anna says she will have fish, with potatoes and a salad.",
        3,
    ),
    (
        "b2200000-0000-4000-8000-000000000201",
        "Why does Bill suggest taking the bus to the mall?",
        ["The bus is free", "Taxis are hard to get during rush hour", "The mall is closed to cars", "The bus is faster in every situation"],
        "Taxis are hard to get during rush hour",
        "Bill explains that it is impossible to get a taxi during rush hour.",
        1,
    ),
    (
        "b2200000-0000-4000-8000-000000000202",
        "How long will they wait for the next bus after missing one?",
        ["Five minutes", "Ten minutes", "Twenty minutes", "One hour"],
        "Ten minutes",
        "Bill reassures Joyce that another bus will arrive in 10 minutes.",
        2,
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    for question_id, question_text, options, correct_answer, explanation, order in QUESTION_UPDATES:
        bind.execute(
            sa.text(
                """
                UPDATE listening_questions
                SET question_text = :question_text,
                    options = CAST(:options AS json),
                    correct_answer = :correct_answer,
                    explanation = :explanation,
                    "order" = :question_order
                WHERE id = :question_id
                """
            ),
            {
                "question_id": question_id,
                "question_text": question_text,
                "options": __import__("json").dumps(options),
                "correct_answer": correct_answer,
                "explanation": explanation,
                "question_order": order,
            },
        )


def downgrade() -> None:
    # Restore the original starter prompts without removing the seeded test.
    bind = op.get_bind()
    previous = [
        ("b2200000-0000-4000-8000-000000000101", "What kind of situation is the first recording about?", ["Ordering food", "Booking a hotel", "Buying a train ticket", "Making a doctor's appointment"], "Ordering food", "The recording is titled 'Ordering a Meal' and presents a restaurant ordering conversation."),
        ("b2200000-0000-4000-8000-000000000102", "Where does the conversation most likely take place?", ["At a restaurant", "At a railway station", "At a university library", "At a pharmacy"], "At a restaurant", "The dialogue is a meal-ordering conversation."),
        ("b2200000-0000-4000-8000-000000000103", "Which skill is most useful for this recording?", ["Identifying food and order details", "Following a lecture on biology", "Understanding a weather forecast", "Describing a map route"], "Identifying food and order details", "A restaurant ordering dialogue requires listening for the food and order details."),
        ("b2200000-0000-4000-8000-000000000201", "What is the main topic of the second recording?", ["Transportation", "A job interview", "A family celebration", "A science experiment"], "Transportation", "The recording is titled 'Transportation'."),
        ("b2200000-0000-4000-8000-000000000202", "Which type of information should you listen for most carefully in a transportation conversation?", ["Travel arrangements and journey details", "Ingredients in a recipe", "Names of musical instruments", "Instructions for a laboratory test"], "Travel arrangements and journey details", "Transportation conversations commonly focus on how people travel and the details of a journey."),
    ]
    for question_id, question_text, options, correct_answer, explanation in previous:
        bind.execute(
            sa.text(
                """
                UPDATE listening_questions
                SET question_text = :question_text,
                    options = CAST(:options AS json),
                    correct_answer = :correct_answer,
                    explanation = :explanation
                WHERE id = :question_id
                """
            ),
            {
                "question_id": question_id,
                "question_text": question_text,
                "options": __import__("json").dumps(options),
                "correct_answer": correct_answer,
                "explanation": explanation,
            },
        )
