"""Cross-user API authorization regression tests for all four IELTS skills."""

import pytest

from app.models.speaking_part import SpeakingPart
from app.models.speaking_test import SpeakingTest
from tests.conftest import (
    login,
    register,
    seed_listening,
    seed_reading,
    seed_writing,
)


async def auth(client):
    email, password, _ = await register(client)
    tokens = await login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_reading_attempt_is_private_and_foreign_submit_is_rejected(client, db):
    test = await seed_reading(db)
    owner = await auth(client)
    other = await auth(client)
    started = await client.post(f"/api/v1/reading/tests/{test.id}/start", headers=owner)
    attempt_id = started.json()["attempt_id"]

    assert (await client.get("/api/v1/reading/attempts", headers=other)).json() == []
    assert (await client.get(f"/api/v1/reading/attempts/{attempt_id}", headers=other)).status_code == 404
    question_id = str(test.passages[0].questions[0].id)
    rejected = await client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=other,
        json={"answers": [{"question_id": question_id, "answer": "Paris"}]},
    )
    assert rejected.status_code == 404
    assert (await client.get(f"/api/v1/reading/attempts/{attempt_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_listening_attempt_is_private_and_foreign_submit_is_rejected(client, db):
    test = await seed_listening(db)
    owner = await auth(client)
    other = await auth(client)
    started = await client.post(f"/api/v1/listening/tests/{test.id}/start", headers=owner)
    attempt_id = started.json()["attempt_id"]

    assert (await client.get("/api/v1/listening/attempts", headers=other)).json() == []
    assert (await client.get(f"/api/v1/listening/attempts/{attempt_id}", headers=other)).status_code == 404
    question_id = str(test.sections[0].questions[0].id)
    rejected = await client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=other,
        json={"answers": [{"question_id": question_id, "answer": "London"}]},
    )
    assert rejected.status_code == 404
    assert (await client.get(f"/api/v1/listening/attempts/{attempt_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_writing_attempt_and_submission_are_private(client, db):
    test = await seed_writing(db)
    owner = await auth(client)
    other = await auth(client)
    started = await client.post(f"/api/v1/writing/tests/{test.id}/start", headers=owner)
    attempt_id = started.json()["attempt_id"]

    assert (await client.get("/api/v1/writing/attempts", headers=other)).json() == []
    assert (await client.get(f"/api/v1/writing/attempts/{attempt_id}", headers=other)).status_code == 404
    task = test.tasks[0]
    rejected_edit = await client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task.id}",
        headers=other,
        json={"response_text": "Unauthorized draft"},
    )
    assert rejected_edit.status_code == 404
    assert (await client.get(f"/api/v1/writing/attempts/{attempt_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_speaking_attempt_and_response_are_private(client, db):
    test = SpeakingTest(
        title="Ownership Speaking Test",
        description="Authorization fixture",
        test_type="academic",
        difficulty="medium",
        time_limit_minutes=15,
    )
    test.parts = [
        SpeakingPart(
            part_number=number,
            title=f"Part {number}",
            instructions="Respond to the prompt.",
            prompt=f"Prompt {number}",
            preparation_seconds=0,
            response_seconds=60,
            order=number,
        )
        for number in (1, 2, 3)
    ]
    db.add(test)
    await db.commit()

    owner = await auth(client)
    other = await auth(client)
    started = await client.post(f"/api/v1/speaking/tests/{test.id}/start", headers=owner)
    attempt_id = started.json()["attempt_id"]
    part_id = test.parts[0].id
    saved = await client.put(
        f"/api/v1/speaking/attempts/{attempt_id}/parts/{part_id}",
        headers=owner,
        json={"transcript": "Owner-only transcript"},
    )
    response_id = saved.json()["response_id"]

    assert (await client.get("/api/v1/speaking/attempts", headers=other)).json() == []
    assert (await client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=other)).status_code == 404
    assert (await client.put(
        f"/api/v1/speaking/attempts/{attempt_id}/parts/{part_id}",
        headers=other,
        json={"transcript": "Unauthorized overwrite"},
    )).status_code == 404
    assert (await client.post(
        f"/api/v1/speaking/responses/{response_id}/evaluate", headers=other
    )).status_code == 404
    detail = (await client.get(f"/api/v1/speaking/attempts/{attempt_id}", headers=owner)).json()
    assert detail["responses"][0]["transcript"] == "Owner-only transcript"
