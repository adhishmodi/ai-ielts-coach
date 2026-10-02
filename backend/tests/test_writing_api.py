import pytest
from tests.conftest import seed_writing,register,login

async def headers(client):
    e,p,_=await register(client); t=await login(client,e,p)
    return {"Authorization":f"Bearer {t['access_token']}"}

@pytest.mark.asyncio
async def test_writing_auth_required(client):
    assert (await client.get("/api/v1/writing/tests")).status_code in (401,403)

@pytest.mark.asyncio
async def test_writing_list_detail_start(client,db):
    test=await seed_writing(db); h=await headers(client)
    assert len((await client.get("/api/v1/writing/tests",headers=h)).json())==1
    assert (await client.get(f"/api/v1/writing/tests/{test.id}",headers=h)).status_code==200
    r=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h)
    assert r.status_code==200 and r.json()["status"]=="in_progress"

@pytest.mark.asyncio
async def test_writing_draft_and_update(client,db):
    test=await seed_writing(db); h=await headers(client)
    s=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]
    task=str(test.tasks[0].id)
    r=await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{task}",headers=h,json={"response_text":"one two three"})
    assert r.status_code==200 and r.json()["word_count"]==3
    r=await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{task}",headers=h,json={"response_text":"one two"})
    assert r.status_code==200 and r.json()["word_count"]==2

@pytest.mark.asyncio
async def test_writing_submit_requires_all_tasks(client,db):
    test=await seed_writing(db); h=await headers(client)
    s=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]
    await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{test.tasks[0].id}",headers=h,json={"response_text":"one"})
    assert (await client.post(f"/api/v1/writing/attempts/{aid}/submit",headers=h)).status_code==400

@pytest.mark.asyncio
async def test_writing_submit_and_attempts(client,db):
    test=await seed_writing(db); h=await headers(client)
    s=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]
    for task in test.tasks:
        await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{task.id}",headers=h,json={"response_text":" ".join(["word"]*task.minimum_words)})
    r=await client.post(f"/api/v1/writing/attempts/{aid}/submit",headers=h)
    assert r.status_code==200 and r.json()["status"]=="submitted" and r.json()["below_minimum_tasks"]==[]
    assert (await client.get("/api/v1/writing/attempts",headers=h)).status_code==200

@pytest.mark.asyncio
async def test_writing_cannot_edit_after_submit(client,db):
    test=await seed_writing(db); h=await headers(client)
    s=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]
    for task in test.tasks:
        await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{task.id}",headers=h,json={"response_text":" ".join(["word"]*task.minimum_words)})
    await client.post(f"/api/v1/writing/attempts/{aid}/submit",headers=h)
    r=await client.put(f"/api/v1/writing/attempts/{aid}/tasks/{test.tasks[0].id}",headers=h,json={"response_text":"changed"})
    assert r.status_code==400

@pytest.mark.asyncio
async def test_writing_attempt_detail(client,db):
    test=await seed_writing(db); h=await headers(client)
    s=await client.post(f"/api/v1/writing/tests/{test.id}/start",headers=h)
    r=await client.get(f"/api/v1/writing/attempts/{s.json()['attempt_id']}",headers=h)
    assert r.status_code==200 and r.json()["submissions"]==[]

@pytest.mark.asyncio
async def test_writing_not_found(client):
    import uuid
    h=await headers(client)
    assert (await client.get(f"/api/v1/writing/tests/{uuid.uuid4()}",headers=h)).status_code==404
    assert (await client.post(f"/api/v1/writing/tests/{uuid.uuid4()}/start",headers=h)).status_code==404
