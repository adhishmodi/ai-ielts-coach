import os
os.environ["ENV_FILE"] = ".env.test"

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import AsyncSessionLocal
from app.models.passage import Passage
from app.models.reading_question import ReadingQuestion
from app.models.reading_test import ReadingTest
from app.models.listening_test import ListeningTest
from app.models.listening_section import ListeningSection
from app.models.listening_question import ListeningQuestion




@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    email = f"reading-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Reading Test User",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }

@pytest.fixture
def second_auth_headers(client):
    email = f"reading-second-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Second Reading User",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }

@pytest.fixture
async def reading_test():
    async with AsyncSessionLocal() as session:
        test = ReadingTest(
            title="IELTS Academic Reading Practice",
            description="A complete reading practice test",
            difficulty="medium",
            time_limit_minutes=60,
        )

        passage1 = Passage(
            title="The History of Coffee",
            content=(
                "Coffee originated in Ethiopia and later spread "
                "throughout the world."
            ),
            order=1,
        )

        passage2 = Passage(
            title="Modern Technology",
            content=(
                "Technology has changed the way people communicate "
                "and work."
            ),
            order=2,
        )

        question1 = ReadingQuestion(
            question_text="Where did coffee originate?",
            question_type="multiple_choice",
            options=[
                "Ethiopia",
                "India",
                "Brazil",
                "France",
            ],
            correct_answer="Ethiopia",
            explanation="The passage states that coffee originated in Ethiopia.",
            order=1,
        )

        question2 = ReadingQuestion(
            question_text="Technology has changed communication.",
            question_type="true_false",
            correct_answer="TRUE",
            explanation="The passage explicitly states this.",
            order=2,
        )

        question3 = ReadingQuestion(
            question_text="What has technology changed?",
            question_type="short_answer",
            correct_answer="communication and work",
            explanation="The passage mentions communication and work.",
            order=1,
        )

        passage1.questions.extend([
            question1,
            question2,
        ])

        passage2.questions.append(question3)

        test.passages.extend([
            passage1,
            passage2,
        ])

        session.add(test)
        await session.commit()
        await session.refresh(test)

        test_id = test.id

    return test_id


@pytest.fixture
async def listening_test():
    async with AsyncSessionLocal() as session:
        test = ListeningTest(
            title="IELTS Academic Listening Practice",
            description="A complete listening practice test",
            difficulty="medium",
            time_limit_minutes=40,
        )

        section1 = ListeningSection(
            title="Section 1 - Social Conversation",
            instructions="Listen and complete the answers.",
            order=1,
        )
        section2 = ListeningSection(
            title="Section 2 - Monologue",
            instructions="Listen and choose the correct answers.",
            order=2,
        )

        questions1 = [
            ListeningQuestion(
                question_text="What is the caller's surname?",
                question_type="short_answer",
                correct_answer="Patel",
                explanation="The caller gives the surname Patel.",
                order=1,
            ),
            ListeningQuestion(
                question_text="What day is the appointment?",
                question_type="short_answer",
                correct_answer="Monday",
                explanation="The appointment is on Monday.",
                order=2,
            ),
            ListeningQuestion(
                question_text="Which service is requested?",
                question_type="multiple_choice",
                options=["Delivery", "Collection", "Repair", "Refund"],
                correct_answer="Delivery",
                explanation="The caller requests delivery.",
                order=3,
            ),
        ]

        section1.questions.extend(questions1)

        section2.questions.append(
            ListeningQuestion(
                question_text="What should visitors bring?",
                question_type="note_completion",
                correct_answer="ID",
                explanation="Visitors must bring ID.",
                order=1,
            )
        )

        test.sections.extend([section1, section2])
        session.add(test)
        await session.commit()
        await session.refresh(test)

        return test.id


@pytest.fixture
async def writing_test():
    from app.models.writing_test import WritingTest
    from app.models.writing_task import WritingTask

    async with AsyncSessionLocal() as session:
        test = WritingTest(
            title="IELTS Academic Writing Practice",
            description="Academic Writing Task 1 and Task 2 practice",
            test_type="academic",
            difficulty="medium",
            time_limit_minutes=60,
        )
        task1 = WritingTask(
            task_number=1,
            task_type="graph",
            prompt="The chart shows changes in household spending over a ten-year period. Summarise the information by selecting and reporting the main features.",
            instructions="Write at least 150 words.",
            minimum_words=150,
            order=1,
        )
        task2 = WritingTask(
            task_number=2,
            task_type="essay",
            prompt="Some people believe technology makes life easier, while others think it creates new problems. Discuss both views and give your own opinion.",
            instructions="Write at least 250 words.",
            minimum_words=250,
            order=2,
        )
        test.tasks.extend([task1, task2])
        session.add(test)
        await session.commit()
        await session.refresh(test)
        return test.id
