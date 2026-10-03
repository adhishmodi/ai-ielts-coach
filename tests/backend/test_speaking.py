import uuid

import pytest
from httpx import Response
from unittest.mock import AsyncMock

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.speaking_part import SpeakingPart
from app.models.speaking_test import SpeakingTest
from app.services.speaking import calculate_speaking_band, calculate_speaking_overall_band


async def seed_speaking_test() -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        test = SpeakingTest(
            title=f"Speaking Practice {uuid.uuid4()}",
            description="IELTS Speaking Parts 1, 2 and 3",
            test_type="academic",
            difficulty="medium",
            time_limit_minutes=15,
        )
        test.parts.extend([
            SpeakingPart(part_number=1, title="Introduction and Interview", instructions="Answer short personal questions.", prompt="Let's talk about your hometown. What do you like about it?", preparation_seconds=0, response_seconds=60, order=1),
            SpeakingPart(part_number=2, title="Long Turn", instructions="Prepare for one minute, then speak for up to two minutes.", prompt="Describe a useful skill you learned.", preparation_seconds=60, response_seconds=120, order=2),
            SpeakingPart(part_number=3, title="Discussion", instructions="Discuss the topic in more depth.", prompt="Why are practical skills important in modern life?", preparation_seconds=0, response_seconds=120, order=3),
        ])
        session.add(test)
        await session.commit()
        return test.id


def test_speaking_scoring_rounds_to_half_band():
    assert calculate_speaking_band(7.0, 7.5, 6.5, 7.0) == 7.0
    assert calculate_speaking_overall_band([6.5, 7.0, 7.5]) == 7.0


def test_speaking_scoring_rejects_empty_parts():
    with pytest.raises(ValueError):
        calculate_speaking_overall_band([])


def test_speaking_requires_auth(client):
    response = client.get("/api/v1/speaking/tests")
    assert response.status_code in (401, 403)


def test_speaking_list_detail_and_start(client, auth_headers):
    test_id = __import__("asyncio").run(seed_speaking_test())
    response = client.get("/api/v1/speaking/tests", headers=auth_headers)
    assert response.status_code == 200
    assert any(item["id"] == str(test_id) for item in response.json())

    detail = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert [part["part_number"] for part in detail.json()["parts"]] == [1, 2, 3]

    started = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"


def test_speaking_draft_submit_and_detail(client, auth_headers):
    test_id = __import__("asyncio").run(seed_speaking_test())
    start = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()
    attempt_id = start["attempt_id"]
    test = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers).json()

    for part in test["parts"]:
        saved = client.put(
            f"/api/v1/speaking/attempts/{attempt_id}/parts/{part['id']}",
            headers=auth_headers,
            json={"transcript": f"This is my response for part {part['part_number']}."},
        )
        assert saved.status_code == 200

    submitted = client.post(f"/api/v1/speaking/attempts/{attempt_id}/submit", headers=auth_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    detail = client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert len(detail.json()["responses"]) == 3


def test_speaking_submit_rejects_missing_parts(client, auth_headers):
    test_id = __import__("asyncio").run(seed_speaking_test())
    attempt_id = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()["attempt_id"]
    test = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers).json()
    part = test["parts"][0]
    client.put(
        f"/api/v1/speaking/attempts/{attempt_id}/parts/{part['id']}",
        headers=auth_headers,
        json={"transcript": "Only one part is answered."},
    )
    response = client.post(f"/api/v1/speaking/attempts/{attempt_id}/submit", headers=auth_headers)
    assert response.status_code == 400
    assert "Missing parts" in response.json()["detail"]


def test_speaking_cannot_edit_after_submit(client, auth_headers):
    test_id = __import__("asyncio").run(seed_speaking_test())
    test = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers).json()
    attempt_id = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()["attempt_id"]
    for part in test["parts"]:
        client.put(f"/api/v1/speaking/attempts/{attempt_id}/parts/{part['id']}", headers=auth_headers, json={"transcript": "Complete response."})
    assert client.post(f"/api/v1/speaking/attempts/{attempt_id}/submit", headers=auth_headers).status_code == 200
    response = client.put(f"/api/v1/speaking/attempts/{attempt_id}/parts/{test['parts'][0]['id']}", headers=auth_headers, json={"transcript": "Changed."})
    assert response.status_code == 400


def test_speaking_attempt_ownership(client, auth_headers, second_auth_headers):
    test_id = __import__("asyncio").run(seed_speaking_test())
    attempt_id = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()["attempt_id"]
    response = client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=second_auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_gemini_speaking_evaluator(monkeypatch):
    from app.services.speaking import GeminiSpeakingEvaluator

    payload = {
        "candidates": [{"content": {"parts": [{"text": '{"fluency_band": 7.0, "lexical_band": 7.5, "grammar_band": 7.0, "pronunciation_band": 6.5, "feedback": "Good response", "strengths": ["Fluent"], "improvements": ["Develop ideas"]}' }]}}]
    }
    response = Response(200, json=payload)
    mock_client = AsyncMock()
    mock_client.post.return_value = response

    class FakeClient:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.services.speaking.httpx.AsyncClient", lambda **kwargs: FakeClient())
    evaluator = GeminiSpeakingEvaluator("key", "gemini-test")
    result = await evaluator.evaluate("I enjoy learning new skills because they help me work independently.", "Describe a useful skill you learned.", 2)
    assert result.overall_band == 7.0
    assert result.strengths == ["Fluent"]


def test_speaking_evaluate_requires_configuration(client, auth_headers, monkeypatch):
    test_id = __import__("asyncio").run(seed_speaking_test())
    test = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers).json()
    attempt_id = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()["attempt_id"]
    for part in test["parts"]:
        client.put(f"/api/v1/speaking/attempts/{attempt_id}/parts/{part['id']}", headers=auth_headers, json={"transcript": "Complete response."})
    client.post(f"/api/v1/speaking/attempts/{attempt_id}/submit", headers=auth_headers)
    detail = client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=auth_headers).json()
    monkeypatch.setattr(settings, "gemini_api_key", None)
    response = client.post(f"/api/v1/speaking/responses/{detail['responses'][0]['id']}/evaluate", headers=auth_headers)
    assert response.status_code == 503


def test_speaking_ai_evaluation_and_final_band(client, auth_headers, monkeypatch):
    test_id = __import__("asyncio").run(seed_speaking_test())
    test = client.get(f"/api/v1/speaking/tests/{test_id}", headers=auth_headers).json()
    attempt_id = client.post(f"/api/v1/speaking/tests/{test_id}/start", headers=auth_headers).json()["attempt_id"]
    for part in test["parts"]:
        client.put(f"/api/v1/speaking/attempts/{attempt_id}/parts/{part['id']}", headers=auth_headers, json={"transcript": "I would like to explain my answer in detail."})
    assert client.post(f"/api/v1/speaking/attempts/{attempt_id}/submit", headers=auth_headers).status_code == 200
    detail = client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=auth_headers).json()

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    scores = iter([6.5, 7.0, 7.5])

    async def fake_evaluate(self, transcript, prompt, part_number):
        from app.services.speaking import DetailedSpeakingEvaluationResult
        score = next(scores)
        return DetailedSpeakingEvaluationResult(score, score, score, score, score, "Feedback", ["Strength"], ["Improve"])

    monkeypatch.setattr("app.api.v1.speaking.GeminiSpeakingEvaluator.evaluate", fake_evaluate)
    for response in detail["responses"]:
        evaluated = client.post(f"/api/v1/speaking/responses/{response['id']}/evaluate", headers=auth_headers)
        assert evaluated.status_code == 200

    final = client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=auth_headers).json()
    assert final["status"] == "evaluated"
    assert final["overall_band"] == 7.0
