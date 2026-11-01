"""Seed deterministic Reading and Speaking content for isolated browser tests only."""
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.reading_test import ReadingTest
from app.models.passage import Passage
from app.models.reading_question import ReadingQuestion
from app.models.speaking_test import SpeakingTest
from app.models.speaking_part import SpeakingPart


async def main() -> None:
    async with AsyncSessionLocal() as session:
        reading = await session.scalar(select(ReadingTest).where(ReadingTest.title == "E2E Reading Test"))
        if reading is None:
            reading = ReadingTest(
                title="E2E Reading Test",
                description="Deterministic test content for browser automation.",
                difficulty="easy",
                time_limit_minutes=60,
            )
            reading.passages = [
                Passage(
                    title="Passage 1",
                    content="The city library opened in 1998. It welcomes visitors every weekday. Researchers describe its quiet reading rooms as essential to the community.",
                    order=1,
                    questions=[
                        ReadingQuestion(
                            question_text="In which year did the library open?",
                            question_type="short_answer",
                            correct_answer="1998",
                            explanation="The passage states that it opened in 1998.",
                            order=1,
                        ),
                        ReadingQuestion(
                            question_text="Which facility opened in 1998?",
                            question_type="multiple_choice",
                            options=["Central Library", "Community Hall", "Sports Centre"],
                            correct_answer="Central Library",
                            explanation="The passage identifies the city library as opening in 1998.",
                            order=2,
                        ),
                        ReadingQuestion(
                            question_text="The library welcomes visitors every weekday.",
                            question_type="true_false",
                            options=["True", "False"],
                            correct_answer="True",
                            explanation="The passage says it welcomes visitors every weekday.",
                            order=3,
                        ),
                        ReadingQuestion(
                            question_text="The library is closed on weekdays.",
                            question_type="true_false_not_given",
                            options=["True", "False", "Not Given"],
                            correct_answer="False",
                            explanation="The passage says it welcomes visitors every weekday.",
                            order=4,
                        ),
                        ReadingQuestion(
                            question_text="Does the passage say the reading rooms are essential to the community?",
                            question_type="yes_no_not_given",
                            options=["Yes", "No", "Not Given"],
                            correct_answer="Yes",
                            explanation="The passage describes the reading rooms as essential to the community.",
                            order=5,
                        ),
                        ReadingQuestion(
                            question_text="The library opened in ____.",
                            question_type="sentence_completion",
                            correct_answer="1998",
                            explanation="The passage gives the opening year as 1998.",
                            order=6,
                        ),
                        ReadingQuestion(
                            question_text="Complete the summary: The library welcomes visitors every ____.",
                            question_type="summary_completion",
                            correct_answer="weekday",
                            explanation="The passage says visitors are welcome every weekday.",
                            order=7,
                        ),
                        ReadingQuestion(
                            question_text="Match the facility to its opening year: Central Library.",
                            question_type="matching",
                            options=["1998", "2005", "2012"],
                            correct_answer="1998",
                            explanation="The passage states that the city library opened in 1998.",
                            order=8,
                        ),
                    ],
                ),
            ]
            session.add(reading)

        speaking = await session.scalar(select(SpeakingTest).where(SpeakingTest.title == "E2E Speaking Test"))
        if speaking is None:
            speaking = SpeakingTest(
                title="E2E Speaking Test",
                description="Deterministic test content for browser automation.",
                test_type="academic",
                difficulty="easy",
                time_limit_minutes=3,
            )
            speaking.parts = [
                SpeakingPart(
                    part_number=1,
                    title="Part 1",
                    instructions="Answer the introductory question.",
                    prompt="Tell me about a skill you enjoy learning.",
                    preparation_seconds=30,
                    response_seconds=120,
                    order=1,
                ),
                SpeakingPart(
                    part_number=2,
                    title="Part 2",
                    instructions="Speak about the topic.",
                    prompt="Describe a skill you would like to learn.",
                    preparation_seconds=1,
                    response_seconds=120,
                    order=2,
                ),
                SpeakingPart(
                    part_number=3,
                    title="Part 3",
                    instructions="Discuss the topic in more depth.",
                    prompt="Why is lifelong learning important?",
                    preparation_seconds=0,
                    response_seconds=120,
                    order=3,
                ),
            ]
            session.add(speaking)

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
