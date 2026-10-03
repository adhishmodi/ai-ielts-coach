from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id
from app.config import settings
from app.database import get_db
from app.models.speaking_attempt import SpeakingAttempt
from app.models.speaking_evaluation import SpeakingEvaluation
from app.models.speaking_part import SpeakingPart
from app.models.speaking_response import SpeakingResponse
from app.models.speaking_test import SpeakingTest
from app.schemas.speaking import (
    SpeakingAttemptDetailResponse,
    SpeakingAttemptResponse,
    SpeakingAttemptStartResponse,
    SpeakingDraftRequest,
    SpeakingDraftResponse,
    SpeakingEvaluateResponse,
    SpeakingResponseDetail,
    SpeakingSubmitResponse,
    SpeakingTestResponse,
)
from app.services.speaking import GeminiSpeakingEvaluator, calculate_speaking_overall_band

router = APIRouter(prefix="/speaking", tags=["Speaking"])


async def _owned_attempt(db: AsyncSession, attempt_id: UUID, user_id: str) -> SpeakingAttempt | None:
    result = await db.execute(
        select(SpeakingAttempt)
        .where(SpeakingAttempt.id == attempt_id, SpeakingAttempt.user_id == user_id)
        .options(
            selectinload(SpeakingAttempt.speaking_test).selectinload(SpeakingTest.parts),
            selectinload(SpeakingAttempt.responses).selectinload(SpeakingResponse.part),
            selectinload(SpeakingAttempt.responses).selectinload(SpeakingResponse.evaluation),
        )
    )
    return result.scalars().unique().first()


@router.get("/tests", response_model=list[SpeakingTestResponse])
async def get_speaking_tests(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(SpeakingTest)
        .options(selectinload(SpeakingTest.parts))
        .order_by(SpeakingTest.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/tests/{test_id}", response_model=SpeakingTestResponse)
async def get_speaking_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(SpeakingTest).where(SpeakingTest.id == test_id).options(selectinload(SpeakingTest.parts))
    )
    speaking_test = result.scalars().unique().first()
    if speaking_test is None:
        raise HTTPException(status_code=404, detail="Speaking test not found")
    return speaking_test


@router.post("/tests/{test_id}/start", response_model=SpeakingAttemptStartResponse)
async def start_speaking_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(SpeakingTest).where(SpeakingTest.id == test_id).options(selectinload(SpeakingTest.parts))
    )
    speaking_test = result.scalars().unique().first()
    if speaking_test is None:
        raise HTTPException(status_code=404, detail="Speaking test not found")
    if len(speaking_test.parts) != 3:
        raise HTTPException(status_code=400, detail="Speaking test must contain Parts 1, 2 and 3")

    attempt = SpeakingAttempt(user_id=current_user_id, speaking_test_id=test_id)
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return SpeakingAttemptStartResponse(
        attempt_id=attempt.id,
        speaking_test_id=attempt.speaking_test_id,
        started_at=attempt.started_at,
        status=attempt.status,
    )


@router.put("/attempts/{attempt_id}/parts/{part_id}", response_model=SpeakingDraftResponse)
async def save_speaking_response(
    attempt_id: UUID,
    part_id: UUID,
    draft: SpeakingDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Speaking attempt not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Speaking attempt is no longer editable")

    part = next((item for item in attempt.speaking_test.parts if item.id == part_id), None)
    if part is None:
        raise HTTPException(status_code=400, detail="Part does not belong to this speaking test")

    response = next((item for item in attempt.responses if item.part_id == part_id), None)
    if response is None:
        response = SpeakingResponse(
            attempt_id=attempt.id, part_id=part.id, transcript=draft.transcript.strip(),
            audio_url=draft.audio_url, duration_seconds=draft.duration_seconds,
        )
        db.add(response)
    else:
        response.transcript = draft.transcript.strip()
        response.audio_url = draft.audio_url
        response.duration_seconds = draft.duration_seconds
        response.submitted_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(response)
    return SpeakingDraftResponse(
        response_id=response.id, attempt_id=attempt.id, part_id=part.id,
        transcript=response.transcript, audio_url=response.audio_url,
        duration_seconds=response.duration_seconds, submitted_at=response.submitted_at,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=SpeakingSubmitResponse)
async def submit_speaking_test(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Speaking attempt not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Speaking attempt has already been submitted")

    missing = [part.part_number for part in attempt.speaking_test.parts if not any(r.part_id == part.id for r in attempt.responses)]
    if missing:
        raise HTTPException(status_code=400, detail=f"All speaking parts must be answered before submission. Missing parts: {missing}")

    now = datetime.now(UTC)
    attempt.submitted_at = now
    attempt.status = "submitted"
    await db.commit()
    await db.refresh(attempt)
    return SpeakingSubmitResponse(attempt_id=attempt.id, status=attempt.status, submitted_at=attempt.submitted_at, missing_parts=[])


@router.get("/attempts", response_model=list[SpeakingAttemptResponse])
async def get_speaking_attempts(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(SpeakingAttempt).where(SpeakingAttempt.user_id == current_user_id).order_by(SpeakingAttempt.started_at.desc())
    )
    return [
        SpeakingAttemptResponse(
            attempt_id=item.id, speaking_test_id=item.speaking_test_id, status=item.status,
            started_at=item.started_at, submitted_at=item.submitted_at,
            overall_band=float(item.overall_band) if item.overall_band is not None else None,
        )
        for item in result.scalars().all()
    ]


@router.get("/attempts/{attempt_id}", response_model=SpeakingAttemptDetailResponse)
async def get_speaking_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Speaking attempt not found")
    return SpeakingAttemptDetailResponse(
        attempt_id=attempt.id, speaking_test_id=attempt.speaking_test_id, status=attempt.status,
        started_at=attempt.started_at, submitted_at=attempt.submitted_at,
        overall_band=float(attempt.overall_band) if attempt.overall_band is not None else None,
        responses=[SpeakingResponseDetail.model_validate(item) for item in attempt.responses],
    )


@router.post("/responses/{response_id}/evaluate", response_model=SpeakingEvaluateResponse)
async def evaluate_speaking_response(
    response_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(SpeakingResponse)
        .join(SpeakingAttempt, SpeakingAttempt.id == SpeakingResponse.attempt_id)
        .where(SpeakingResponse.id == response_id, SpeakingAttempt.user_id == current_user_id)
        .options(selectinload(SpeakingResponse.part), selectinload(SpeakingResponse.evaluation), selectinload(SpeakingResponse.attempt))
    )
    response = result.scalars().first()
    if response is None:
        raise HTTPException(status_code=404, detail="Speaking response not found")
    if response.attempt.status == "in_progress":
        raise HTTPException(status_code=400, detail="Submit the speaking attempt before evaluation")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI evaluation is not configured")

    evaluator = GeminiSpeakingEvaluator(settings.gemini_api_key, settings.gemini_model)
    try:
        evaluated = await evaluator.evaluate(response.transcript, response.part.prompt, response.part.part_number)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI evaluation failed: {exc}") from exc

    evaluation = response.evaluation
    if evaluation is None:
        evaluation = SpeakingEvaluation(response_id=response.id)
        db.add(evaluation)
    evaluation.fluency_band = evaluated.fluency_band
    evaluation.lexical_band = evaluated.lexical_band
    evaluation.grammar_band = evaluated.grammar_band
    evaluation.pronunciation_band = evaluated.pronunciation_band
    evaluation.overall_band = evaluated.overall_band
    evaluation.feedback = evaluated.feedback
    evaluation.strengths = evaluated.strengths
    evaluation.improvements = evaluated.improvements
    evaluation.evaluated_by = evaluated.evaluated_by
    evaluation.evaluated_at = datetime.now(UTC)
    await db.flush()

    evaluated_result = await db.execute(
        select(SpeakingEvaluation, SpeakingPart.part_number)
        .join(SpeakingResponse, SpeakingResponse.id == SpeakingEvaluation.response_id)
        .join(SpeakingPart, SpeakingPart.id == SpeakingResponse.part_id)
        .where(SpeakingResponse.attempt_id == response.attempt_id)
    )
    evaluated_rows = evaluated_result.all()
    response_status = response.attempt.status
    if len(evaluated_rows) == 3:
        part_bands = [float(item.overall_band) for item, _ in evaluated_rows]
        response.attempt.overall_band = calculate_speaking_overall_band(part_bands)
        response.attempt.status = "evaluated"
        response_status = "evaluated"

    await db.commit()
    await db.refresh(evaluation)
    return SpeakingEvaluateResponse(response_id=response.id, status=response_status, evaluation=evaluation)
