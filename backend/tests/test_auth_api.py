import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.refresh_session import RefreshSession
from app.services.refresh_token import hash_refresh_token
from tests.conftest import register, login


@pytest.mark.asyncio
async def test_register(client):
    email,password,body=await register(client)
    assert body["email"]==email and body["full_name"]=="Test User" and body["id"]

@pytest.mark.asyncio
async def test_duplicate_register(client):
    email,password,_=await register(client)
    r=await client.post("/api/v1/auth/register",json={"email":email,"password":password,"full_name":"Other User"})
    assert r.status_code==409

@pytest.mark.asyncio
@pytest.mark.parametrize("password",["short","1234567"])
async def test_short_password(client,password):
    r=await client.post("/api/v1/auth/register",json={"email":"a@example.com","password":password,"full_name":"Valid User"})
    assert r.status_code==422

@pytest.mark.asyncio
async def test_login(client):
    email,password,_=await register(client)
    t=await login(client,email,password)
    assert t["token_type"]=="bearer" and t["access_token"] and t["refresh_token"]

@pytest.mark.asyncio
async def test_bad_login(client):
    email,_,_=await register(client)
    assert (await client.post("/api/v1/auth/login",json={"email":email,"password":"WrongPassword!"})).status_code==401
    assert (await client.post("/api/v1/auth/login",json={"email":"missing@example.com","password":"Password123!"})).status_code==401

@pytest.mark.asyncio
async def test_refresh_and_logout(client):
    email,password,_=await register(client)
    t=await login(client,email,password)
    assert (await client.post("/api/v1/auth/refresh",json={"refresh_token":t["refresh_token"]})).status_code==200
    assert (await client.post("/api/v1/auth/logout",json={"refresh_token":t["refresh_token"]})).status_code==200
    assert (await client.post("/api/v1/auth/refresh",json={"refresh_token":t["refresh_token"]})).status_code==401

@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected(client, db):
    email,password,_=await register(client)
    tokens=await login(client,email,password)
    session=await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(tokens["refresh_token"])
        )
    )
    assert session is not None
    session.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    await db.commit()

    response=await client.post("/api/v1/auth/refresh",json={"refresh_token":tokens["refresh_token"]})
    assert response.status_code==401
    assert response.json()["detail"]=="Refresh token has expired"

@pytest.mark.asyncio
async def test_bad_logout(client):
    assert (await client.post("/api/v1/auth/logout",json={"refresh_token":"bad"})).status_code==401

@pytest.mark.asyncio
async def test_user_me_and_update(client):
    email,password,_=await register(client,full_name="Original Name")
    t=await login(client,email,password)
    h={"Authorization":f"Bearer {t['access_token']}"}
    assert (await client.get("/api/v1/users/me",headers=h)).json()["full_name"]=="Original Name"
    r=await client.patch("/api/v1/users/me",headers=h,json={"full_name":"Updated Name"})
    assert r.status_code==200 and r.json()["full_name"]=="Updated Name"

@pytest.mark.asyncio
async def test_auth_required(client):
    assert (await client.get("/api/v1/users/me")).status_code in (401,403)
