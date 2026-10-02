import os
os.environ.setdefault("ENV_FILE", ".env")
os.environ.setdefault("TESTING", "1")

import uuid
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.refresh_session import RefreshSession
from app.models.reading_answer import ReadingAnswer
from app.models.reading_attempt import ReadingAttempt
from app.models.reading_question import ReadingQuestion
from app.models.passage import Passage
from app.models.reading_test import ReadingTest
from app.models.listening_answer import ListeningAnswer
from app.models.listening_attempt import ListeningAttempt
from app.models.listening_question import ListeningQuestion
from app.models.listening_section import ListeningSection
from app.models.listening_test import ListeningTest
from app.models.writing_evaluation import WritingEvaluation
from app.models.writing_submission import WritingSubmission
from app.models.writing_attempt import WritingAttempt
from app.models.writing_task import WritingTask
from app.models.writing_test import WritingTest

@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    async with AsyncSessionLocal() as session:
        for model in (
            WritingEvaluation, WritingSubmission, WritingAttempt, WritingTask, WritingTest,
            ListeningAnswer, ListeningAttempt, ListeningQuestion, ListeningSection, ListeningTest,
            ReadingAnswer, ReadingAttempt, ReadingQuestion, Passage, ReadingTest,
            RefreshSession, User,
        ):
            await session.execute(delete(model))
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        for model in (
            WritingEvaluation, WritingSubmission, WritingAttempt, WritingTask, WritingTest,
            ListeningAnswer, ListeningAttempt, ListeningQuestion, ListeningSection, ListeningTest,
            ReadingAnswer, ReadingAttempt, ReadingQuestion, Passage, ReadingTest,
            RefreshSession, User,
        ):
            await session.execute(delete(model))
        await session.commit()

async def register(client, email=None, full_name="Test User", password="Password123!"):
    email = email or f"{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": full_name})
    assert response.status_code == 201, response.text
    return email, password, response.json()

async def login(client, email, password="Password123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()

async def seed_reading(db: AsyncSession):
    test = ReadingTest(title="Reading Test", description="desc", difficulty="medium", time_limit_minutes=60)
    passage = Passage(title="Passage 1", content="A passage", order=1)
    passage.questions = [
        ReadingQuestion(question_text="Q1", question_type="multiple_choice", correct_answer="Paris|paris", order=1, options=["Paris", "Rome"]),
        ReadingQuestion(question_text="Q2", question_type="short_answer", correct_answer="blue", order=2),
    ]
    test.passages = [passage]
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test

async def seed_listening(db: AsyncSession):
    test = ListeningTest(title="Listening Test", description="desc", difficulty="easy", time_limit_minutes=40)
    section = ListeningSection(title="Section 1", instructions="Listen", order=1)
    section.questions = [
        ListeningQuestion(question_text="Q1", question_type="multiple_choice", correct_answer="London|london", order=1, options=["London", "Paris"]),
        ListeningQuestion(question_text="Q2", question_type="short_answer", correct_answer="coffee", order=2),
    ]
    test.sections = [section]
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test

async def seed_writing(db: AsyncSession):
    test = WritingTest(title="Writing Test", description="desc", test_type="academic", difficulty="medium", time_limit_minutes=60)
    test.tasks = [
        WritingTask(task_number=1, task_type="graph", prompt="Describe the graph.", instructions="Write at least 150 words.", minimum_words=150, order=1),
        WritingTask(task_number=2, task_type="essay", prompt="Discuss this topic.", instructions="Write at least 250 words.", minimum_words=250, order=2),
    ]
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test
