import httpx
import pytest

import app.api.v1.speaking as speaking_api
import app.api.v1.writing as writing_api
from app.config import settings
from app.models.speaking_attempt import SpeakingAttempt
from app.models.speaking_part import SpeakingPart
from app.models.speaking_response import SpeakingResponse
from app.models.speaking_test import SpeakingTest
from app.services.speaking import DetailedSpeakingEvaluationResult
from app.services.writing import DetailedWritingEvaluationResult
from tests.conftest import seed_writing, register, login


async def auth_headers(client):
    email, password, _ = await register(client)
    tokens = await login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_writing_provider_timeout_preserves_submission_and_allows_retry(client, db, monkeypatch):
    test = await seed_writing(db)
    headers = await auth_headers(client)
    attempt_id = (await client.post(
        f"/api/v1/writing/tests/{test.id}/start", headers=headers
    )).json()["attempt_id"]
    for task in test.tasks:
        text = " ".join(["answer"] * task.minimum_words)
        saved = await client.put(
            f"/api/v1/writing/attempts/{attempt_id}/tasks/{task.id}",
            headers=headers,
            json={"response_text": text},
        )
        assert saved.status_code == 200
    assert (await client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit", headers=headers
    )).status_code == 200
    detail = (await client.get(
        f"/api/v1/writing/attempts/{attempt_id}", headers=headers
    )).json()
    submission = detail["submissions"][0]
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    class TimeoutEvaluator:
        def __init__(self, *args): pass
        async def evaluate(self, *args):
            raise httpx.ReadTimeout("provider timed out")

    monkeypatch.setattr(writing_api, "GeminiWritingEvaluator", TimeoutEvaluator)
    failed = await client.post(
        f"/api/v1/writing/submissions/{submission['id']}/evaluate", headers=headers
    )
    assert failed.status_code == 502
    assert "saved" in failed.json()["detail"].lower()

    after_failure = (await client.get(
        f"/api/v1/writing/attempts/{attempt_id}", headers=headers
    )).json()
    saved_submission = next(item for item in after_failure["submissions"] if item["id"] == submission["id"])
    assert saved_submission["response_text"] == submission["response_text"]
    assert saved_submission.get("evaluation") is None

    class SuccessEvaluator:
        def __init__(self, *args): pass
        async def evaluate(self, *args):
            return DetailedWritingEvaluationResult(
                task_response_band=6.5, task_achievement_band=None,
                coherence_band=6.5, lexical_band=6.5, grammar_band=6.5,
                overall_band=6.5, feedback="Recovered after timeout",
                strengths=["Relevant"], improvements=["Add detail"],
            )

    monkeypatch.setattr(writing_api, "GeminiWritingEvaluator", SuccessEvaluator)
    retried = await client.post(
        f"/api/v1/writing/submissions/{submission['id']}/evaluate", headers=headers
    )
    assert retried.status_code == 200
    assert retried.json()["evaluation"]["feedback"] == "Recovered after timeout"


async def seed_speaking_attempt(db, user_id):
    test = SpeakingTest(
        title="Evaluator Failure Test", description="Test", test_type="academic",
        difficulty="medium", time_limit_minutes=15,
    )
    test.parts = [
        SpeakingPart(
            part_number=number, title=f"Part {number}", instructions="Answer",
            prompt=f"Prompt {number}", preparation_seconds=0,
            response_seconds=60, order=number,
        )
        for number in (1, 2, 3)
    ]
    db.add(test)
    await db.flush()
    attempt = SpeakingAttempt(user_id=user_id, speaking_test_id=test.id)
    db.add(attempt)
    await db.flush()
    for part in test.parts:
        db.add(SpeakingResponse(
            attempt_id=attempt.id, part_id=part.id, transcript=f"Response {part.part_number}"
        ))
    attempt.status = "submitted"
    await db.commit()
    return attempt.id


@pytest.mark.asyncio
async def test_speaking_provider_timeout_is_user_visible_and_retryable(client, db, monkeypatch):
    email, password, user = await register(client)
    tokens = await login(client, email, password)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    attempt_id = await seed_speaking_attempt(db, user["id"])
    detail = (await client.get(
        f"/api/v1/speaking/attempts/{attempt_id}", headers=headers
    )).json()
    response_id = detail["responses"][0]["id"]
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    class TimeoutEvaluator:
        def __init__(self, *args): pass
        async def evaluate(self, *args):
            raise httpx.ReadTimeout("provider timed out")

    monkeypatch.setattr(speaking_api, "GeminiSpeakingEvaluator", TimeoutEvaluator)
    failed = await client.post(
        f"/api/v1/speaking/responses/{response_id}/evaluate", headers=headers
    )
    assert failed.status_code == 502
    assert "timed out" in failed.json()["detail"].lower()

    class SuccessEvaluator:
        def __init__(self, *args): pass
        async def evaluate(self, *args):
            return DetailedSpeakingEvaluationResult(
                7.0, 7.0, 6.5, 6.5, 7.0, "Recovered feedback", ["Fluent"], ["Examples"]
            )

    monkeypatch.setattr(speaking_api, "GeminiSpeakingEvaluator", SuccessEvaluator)
    retried = await client.post(
        f"/api/v1/speaking/responses/{response_id}/evaluate", headers=headers
    )
    assert retried.status_code == 200
    assert retried.json()["evaluation"]["feedback"] == "Recovered feedback"
