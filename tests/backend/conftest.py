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

