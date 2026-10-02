import pytest
from tests.conftest import seed_reading,register,login

async def headers(client):
    e,p,_=await register(client); t=await login(client,e,p)
    return {"Authorization":f"Bearer {t['access_token']}"}

@pytest.mark.asyncio
async def test_reading_auth_required(client):
    assert (await client.get("/api/v1/reading/tests")).status_code in (401,403)

@pytest.mark.asyncio
async def test_reading_list_detail_start(client,db):
    test=await seed_reading(db); h=await headers(client)
    assert (await client.get("/api/v1/reading/tests",headers=h)).status_code==200
    assert len((await client.get(f"/api/v1/reading/tests/{test.id}",headers=h)).json()["passages"])==1
    start=await client.post(f"/api/v1/reading/tests/{test.id}/start",headers=h)
    assert start.status_code==200

@pytest.mark.asyncio
async def test_reading_submit_and_detail(client,db):
    test=await seed_reading(db); h=await headers(client)
    start=await client.post(f"/api/v1/reading/tests/{test.id}/start",headers=h); aid=start.json()["attempt_id"]
    q=[str(x.id) for x in test.passages[0].questions]
    r=await client.post(f"/api/v1/reading/attempts/{aid}/submit",headers=h,json={"answers":[{"question_id":q[0],"answer":"PARIS"},{"question_id":q[1],"answer":"blue"}]})
    assert r.status_code==200 and r.json()["score"]==2
    d=await client.get(f"/api/v1/reading/attempts/{aid}",headers=h)
    assert d.status_code==200 and len(d.json()["answers"])==2

@pytest.mark.asyncio
async def test_reading_rejects_empty_and_duplicate(client,db):
    test=await seed_reading(db); h=await headers(client)
    s=await client.post(f"/api/v1/reading/tests/{test.id}/start",headers=h); aid=s.json()["attempt_id"]; q=str(test.passages[0].questions[0].id)
    assert (await client.post(f"/api/v1/reading/attempts/{aid}/submit",headers=h,json={"answers":[]})).status_code==400
    assert (await client.post(f"/api/v1/reading/attempts/{aid}/submit",headers=h,json={"answers":[{"question_id":q,"answer":"a"},{"question_id":q,"answer":"b"}]})).status_code==400

@pytest.mark.asyncio
async def test_reading_attempts_list(client,db):
    test=await seed_reading(db); h=await headers(client)
    await client.post(f"/api/v1/reading/tests/{test.id}/start",headers=h)
    r=await client.get("/api/v1/reading/attempts",headers=h)
    assert r.status_code==200 and len(r.json())==1

@pytest.mark.asyncio
async def test_reading_not_found(client):
    import uuid
    h=await headers(client)
    assert (await client.get(f"/api/v1/reading/tests/{uuid.uuid4()}",headers=h)).status_code==404
    assert (await client.post(f"/api/v1/reading/tests/{uuid.uuid4()}/start",headers=h)).status_code==404
