import pytest

from tests.conftest import seed_reading, seed_listening, seed_writing, register, login


async def auth_headers(client):
    email, password, _ = await register(client)
    tokens = await login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("skill,seed,start_path,detail_path,submit_path", [
    ("reading", seed_reading, "/reading/tests/{test_id}/start", "/reading/attempts/{attempt_id}", "/reading/attempts/{attempt_id}/submit"),
    ("listening", seed_listening, "/listening/tests/{test_id}/start", "/listening/attempts/{attempt_id}", "/listening/attempts/{attempt_id}/submit"),
])
async def test_attempt_owner_only_for_reading_and_listening(client, db, skill, seed, start_path, detail_path, submit_path):
    test = await seed(db)
    owner = await auth_headers(client)
    other = await auth_headers(client)
    started = await client.post(
        f"/api/v1{start_path.format(test_id=test.id)}", headers=owner
    )
    assert started.status_code == 200
    attempt_id = started.json()["attempt_id"]

    detail = await client.get(
        f"/api/v1{detail_path.format(attempt_id=attempt_id)}", headers=other
    )
    assert detail.status_code == 404

    question = (test.passages[0].questions[0] if skill == "reading" else test.sections[0].questions[0])
    rejected = await client.post(
        f"/api/v1{submit_path.format(attempt_id=attempt_id)}",
        headers=other,
        json={"answers": [{"question_id": str(question.id), "answer": "unauthorized"}]},
    )
    assert rejected.status_code == 404

    owner_detail = await client.get(
        f"/api/v1{detail_path.format(attempt_id=attempt_id)}", headers=owner
    )
    assert owner_detail.status_code == 200
    assert owner_detail.json().get("answers", []) == []


@pytest.mark.asyncio
async def test_writing_attempt_owner_only_for_draft_and_submit(client, db):
    test = await seed_writing(db)
    owner = await auth_headers(client)
    other = await auth_headers(client)
    started = await client.post(
        f"/api/v1/writing/tests/{test.id}/start", headers=owner
    )
    attempt_id = started.json()["attempt_id"]
    task_id = str(test.tasks[0].id)

    read = await client.get(
        f"/api/v1/writing/attempts/{attempt_id}", headers=other
    )
    assert read.status_code == 404
    draft = await client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=other,
        json={"response_text": "unauthorized draft"},
    )
    assert draft.status_code == 404
    submit = await client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit", headers=other
    )
    assert submit.status_code == 404

    owner_detail = await client.get(
        f"/api/v1/writing/attempts/{attempt_id}", headers=owner
    )
    assert owner_detail.status_code == 200
    assert owner_detail.json()["submissions"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {},
    {"answers": [{"answer": "missing question id"}]},
    {"answers": [{"question_id": "not-a-uuid", "answer": "x"}]},
    {"answers": [{"question_id": "00000000-0000-0000-0000-000000000000", "answer": 123}]},
])
async def test_reading_malformed_submission_payloads_are_rejected(client, db, payload):
    test = await seed_reading(db)
    owner = await auth_headers(client)
    started = await client.post(
        f"/api/v1/reading/tests/{test.id}/start", headers=owner
    )
    response = await client.post(
        f"/api/v1/reading/attempts/{started.json()['attempt_id']}/submit",
        headers=owner,
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_listening_rejects_question_from_another_test(client, db):
    first = await seed_listening(db)
    second = await seed_listening(db)
    owner = await auth_headers(client)
    started = await client.post(
        f"/api/v1/listening/tests/{first.id}/start", headers=owner
    )
    foreign_question = str(second.sections[0].questions[0].id)
    response = await client.post(
        f"/api/v1/listening/attempts/{started.json()['attempt_id']}/submit",
        headers=owner,
        json={"answers": [{"question_id": foreign_question, "answer": "coffee"}]},
    )
    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]
