from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    RefreshTokenRequest
)
from app.services.auth import hash_password, verify_password
from app.services.jwt import create_access_token

from datetime import datetime, timedelta, timezone

from app.models.refresh_session import RefreshSession
from app.services.refresh_token import (
    create_refresh_token,
    hash_refresh_token,
)
from app.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse
)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )

    user = result.scalar_one_or_none()

    if not user or not verify_password(
        user_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create short-lived access token
    access_token = create_access_token(str(user.id))

    # Create long-lived refresh token
    refresh_token = create_refresh_token()

    # Store only the hash of the refresh token
    refresh_session = RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days)
    )

    db.add(refresh_session)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    token_hash = hash_refresh_token(
        token_data.refresh_token
    )

    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    session.revoked_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Logged out successfully"
    }


@router.post(
    "/refresh",
    response_model=TokenResponse
)
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    token_hash = hash_refresh_token(
        token_data.refresh_token
    )

    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )

    if session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )

    access_token = create_access_token(
        str(session.user_id)
    )

    return {
        "access_token": access_token,
        "refresh_token": token_data.refresh_token,
        "token_type": "bearer"
    }