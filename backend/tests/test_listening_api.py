import pytest
from tests.conftest import seed_listening,register,login

async def headers(client):
    e,p,_=await register(client); t=await login(client,e,p)
    return {"Authorization":f"Bearer {t['access_token']}"}

@pytest.mark.asyncio
async def test_listening_auth_required(client):
    assert (await client.get("/api/v1/listening/tests")).status_code in (401,403)

@pytest.mark.asyncio
async def test_listening_list_detail_start(client,db):
    test=await seed_listening(db); h=await headers(client)
    assert (await client.get("/api/v1/listening/tests",headers=h)).status_code==200
    assert len((await client.get(f"/api/v1/listening/tests/{test.id}",headers=h)).json()["sections"])==1
    assert (await client.post(f"/api/v1/listening/tests/{test.id}/start",headers=h)).status_code==200

@pytest.mark.asyncio
async def test_listening_submit_detail(client,db):
    test=await seed_listening(db); h=await headers(client)
    s=await client.post(f"/api/v1/listening/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]
    q=[str(x.id) for x in test.sections[0].questions]
    r=await client.post(f"/api/v1/listening/attempts/{aid}/submit",headers=h,json={"answers":[{"question_id":q[0],"answer":"london"},{"question_id":q[1],"answer":"wrong"}]})
    assert r.status_code==200 and r.json()["score"]==1
    assert len((await client.get(f"/api/v1/listening/attempts/{aid}",headers=h)).json()["answers"])==2

@pytest.mark.asyncio
async def test_listening_rejects_empty_duplicate(client,db):
    test=await seed_listening(db); h=await headers(client)
    s=await client.post(f"/api/v1/listening/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]; q=str(test.sections[0].questions[0].id)
    assert (await client.post(f"/api/v1/listening/attempts/{aid}/submit",headers=h,json={"answers":[]})).status_code==400
    assert (await client.post(f"/api/v1/listening/attempts/{aid}/submit",headers=h,json={"answers":[{"question_id":q,"answer":"a"},{"question_id":q,"answer":"b"}]})).status_code==400

@pytest.mark.asyncio
async def test_listening_not_found(client):
    import uuid
    h=await headers(client)
    assert (await client.get(f"/api/v1/listening/tests/{uuid.uuid4()}",headers=h)).status_code==404
