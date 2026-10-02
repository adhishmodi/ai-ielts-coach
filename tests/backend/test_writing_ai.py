import app.api.v1.writing as writing_api
from app.services.writing import DetailedWritingEvaluationResult


def _get_submission_ids(client, headers, attempt_id):
    detail = client.get(f"/api/v1/writing/attempts/{attempt_id}", headers=headers)
    assert detail.status_code == 200
    return [item["id"] for item in detail.json()["submissions"]]


def test_evaluation_requires_configuration(client, auth_headers, writing_test):
    attempt = client.post(
        f"/api/v1/writing/tests/{writing_test}/start", headers=auth_headers
    ).json()["attempt_id"]
    response = client.get(
        f"/api/v1/writing/tests/{writing_test}", headers=auth_headers
    )
    tasks = {x["task_number"]: x for x in response.json()["tasks"]}
    for number, count in [(1, 150), (2, 250)]:
        assert client.put(
            f"/api/v1/writing/attempts/{attempt}/tasks/{tasks[number]['id']}",
            headers=auth_headers,
            json={"response_text": " ".join(["word"] * count)},
        ).status_code == 200
    assert client.post(
        f"/api/v1/writing/attempts/{attempt}/submit", headers=auth_headers
    ).status_code == 200
    submission_id = _get_submission_ids(client, auth_headers, attempt)[0]
    response = client.post(
        f"/api/v1/writing/submissions/{submission_id}/evaluate",
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_evaluation_rejects_unsubmitted_attempt(client, auth_headers, writing_test, monkeypatch):
    monkeypatch.setattr(writing_api.settings, "gemini_api_key", "test-key")
    attempt = client.post(
        f"/api/v1/writing/tests/{writing_test}/start", headers=auth_headers
    ).json()["attempt_id"]
    response = client.get(
        f"/api/v1/writing/attempts/{attempt}", headers=auth_headers
    )
    assert response.status_code == 200
    response = client.post(
        f"/api/v1/writing/submissions/{attempt}/evaluate",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_gemini_evaluation_persists_feedback_and_scores(
    client, auth_headers, writing_test, monkeypatch
):
    class FakeEvaluator:
        def __init__(self, api_key, model):
            assert api_key == "test-key"

        async def evaluate(self, submission_text, task_prompt, task_type):
            return DetailedWritingEvaluationResult(
                task_response_band=6.5,
                coherence_band=6.0,
                lexical_band=6.5,
                grammar_band=6.0,
                overall_band=6.5,
                feedback="Clear response with room for more precise vocabulary.",
                strengths=["Clear organization"],
                improvements=["Use more precise vocabulary"],
            )

    monkeypatch.setattr(writing_api.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(writing_api, "GeminiWritingEvaluator", FakeEvaluator)

    attempt = client.post(
        f"/api/v1/writing/tests/{writing_test}/start", headers=auth_headers
    ).json()["attempt_id"]
    test_data = client.get(
        f"/api/v1/writing/tests/{writing_test}", headers=auth_headers
    ).json()
    for task in test_data["tasks"]:
        count = task["minimum_words"]
        assert client.put(
            f"/api/v1/writing/attempts/{attempt}/tasks/{task['id']}",
            headers=auth_headers,
            json={"response_text": " ".join(["response"] * count)},
        ).status_code == 200
    assert client.post(
        f"/api/v1/writing/attempts/{attempt}/submit", headers=auth_headers
    ).status_code == 200

    submission_id = _get_submission_ids(client, auth_headers, attempt)[0]
    response = client.post(
        f"/api/v1/writing/submissions/{submission_id}/evaluate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation"]["overall_band"] == 6.5
    assert data["evaluation"]["feedback"].startswith("Clear response")
    assert data["status"] == "submitted"

    second_id = _get_submission_ids(client, auth_headers, attempt)[1]
    assert client.post(
        f"/api/v1/writing/submissions/{second_id}/evaluate",
        headers=auth_headers,
    ).status_code == 200
    detail = client.get(
        f"/api/v1/writing/attempts/{attempt}", headers=auth_headers
    )
    assert detail.json()["status"] == "evaluated"


def test_evaluation_enforces_submission_ownership(
    client, auth_headers, second_auth_headers, writing_test
):
    attempt = client.post(
        f"/api/v1/writing/tests/{writing_test}/start", headers=auth_headers
    ).json()["attempt_id"]
    task = client.get(
        f"/api/v1/writing/tests/{writing_test}", headers=auth_headers
    ).json()["tasks"][0]
    client.put(
        f"/api/v1/writing/attempts/{attempt}/tasks/{task['id']}",
        headers=auth_headers,
        json={"response_text": " ".join(["word"] * 150)},
    )
    submission_id = _get_submission_ids(client, auth_headers, attempt)[0]
    response = client.post(
        f"/api/v1/writing/submissions/{submission_id}/evaluate",
        headers=second_auth_headers,
    )
    assert response.status_code == 404
