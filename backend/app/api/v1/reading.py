from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id
from app.database import get_db
from app.models.passage import Passage
from app.models.reading_answer import ReadingAnswer
from app.models.reading_attempt import ReadingAttempt
from app.models.reading_test import ReadingTest

from app.schemas.reading import (
    ReadingAnswerDetailResponse,
    ReadingAttemptDetailResponse,
    ReadingAttemptResponse,
    ReadingAttemptStartResponse,
    ReadingSubmissionRequest,
    ReadingSubmissionResponse,
    ReadingTestResponse,
)
from app.services.reading import (
    calculate_reading_band,
    calculate_reading_score_by_question_type,
    validate_question_type,
)

router = APIRouter(
    prefix="/reading",
    tags=["Reading"],
)


@router.get("/tests", response_model=list[ReadingTestResponse])
async def get_reading_tests(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingTest)
        .options(
            selectinload(ReadingTest.passages)
            .selectinload(Passage.questions)
        )
        .order_by(ReadingTest.created_at.desc())
    )

    return result.scalars().unique().all()


@router.get("/tests/{test_id}", response_model=ReadingTestResponse)
async def get_reading_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingTest)
        .where(ReadingTest.id == test_id)
        .options(
            selectinload(ReadingTest.passages)
            .selectinload(Passage.questions)
        )
    )

    reading_test = result.scalars().unique().first()

    if reading_test is None:
        raise HTTPException(
            status_code=404,
            detail="Reading test not found",
        )

    return reading_test

@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=ReadingSubmissionResponse,
)
async def submit_reading_test(
    attempt_id: UUID,
    submission: ReadingSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingAttempt)
        .where(
            ReadingAttempt.id == attempt_id,
            ReadingAttempt.user_id == current_user_id,
        )
        .options(
            selectinload(ReadingAttempt.reading_test)
            .selectinload(ReadingTest.passages)
            .selectinload(Passage.questions)
        )
    )

    attempt = result.scalars().unique().first()

    if attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Reading attempt not found",
        )

    if attempt.submitted_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Reading attempt has already been submitted",
        )

    reading_test = attempt.reading_test

    questions = [
        question
        for passage in reading_test.passages
        for question in passage.questions
    ]

    for question in questions:
        if not validate_question_type(question.question_type):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported question type: "
                    f"{question.question_type}"
                ),
            )
    
    if not submission.answers:
        raise HTTPException(
            status_code=400,
            detail="At least one answer is required",
        )

    question_map = {
        str(question.id): question
        for question in questions
    }

    submitted_answers = {}

    for answer in submission.answers:
        question_id = str(answer.question_id)

        if question_id not in question_map:
            raise HTTPException(
                status_code=400,
                detail=f"Question {question_id} does not belong to this test",
            )

        if question_id in submitted_answers:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate answer for question {question_id}",
            )

        submitted_answers[question_id] = answer.answer

    question_data = {
        str(question.id): {
            "correct_answer": question.correct_answer,
            "question_type": question.question_type,
        }
        for question in questions
    }

    score = calculate_reading_score_by_question_type(
        submitted_answers,
        question_data,
    )    
    total_questions = len(questions)

    band_score = calculate_reading_band(
        score,
        total_questions,
    )

    attempt.submitted_at = datetime.now(UTC)
    attempt.score = score
    attempt.band_score = band_score

    for question_id, answer in submitted_answers.items():
        reading_answer = ReadingAnswer(
            attempt=attempt,
            question_id=UUID(question_id),
            answer=answer,
        )
        db.add(reading_answer)

    await db.commit()
    await db.refresh(attempt)

    return ReadingSubmissionResponse(
        attempt_id=attempt.id,
        score=score,
        total_questions=total_questions,
        band_score=float(attempt.band_score),
    )
@router.get(
    "/attempts",
    response_model=list[ReadingAttemptResponse],
)
async def get_reading_attempts(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingAttempt)
        .where(ReadingAttempt.user_id == current_user_id)
        .options(
            selectinload(ReadingAttempt.reading_test)
            .selectinload(ReadingTest.passages)
            .selectinload(Passage.questions)
        )
        .order_by(ReadingAttempt.submitted_at.desc())
    )

    attempts = result.scalars().unique().all()

    return [
        ReadingAttemptResponse(
            attempt_id=attempt.id,
            reading_test_id=attempt.reading_test_id,
            score=attempt.score,
            total_questions=sum(
                len(passage.questions)
                for passage in attempt.reading_test.passages
            ),
            band_score=float(attempt.band_score),
            submitted_at=attempt.submitted_at,
        )
        for attempt in attempts
    ]


@router.get(
    "/attempts/{attempt_id}",
    response_model=ReadingAttemptDetailResponse,
)
async def get_reading_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingAttempt)
        .where(
            ReadingAttempt.id == attempt_id,
            ReadingAttempt.user_id == current_user_id,
        )
        .options(
            selectinload(ReadingAttempt.answers)
            .selectinload(ReadingAnswer.question),
            selectinload(ReadingAttempt.reading_test)
            .selectinload(ReadingTest.passages)
            .selectinload(Passage.questions),
        )
    )

    attempt = result.scalars().unique().first()

    if attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Reading attempt not found",
        )

    answers = [
        ReadingAnswerDetailResponse(
            question_id=answer.question_id,
            question_text=answer.question.question_text,
            question_type=answer.question.question_type,
            user_answer=answer.answer,
            correct_answer=answer.question.correct_answer,
            is_correct=(
                answer.answer.strip().lower()
                == answer.question.correct_answer.strip().lower()
            ),
        )
        for answer in attempt.answers
    ]

    total_questions = sum(
        len(passage.questions)
        for passage in attempt.reading_test.passages
    )

    return ReadingAttemptDetailResponse(
        attempt_id=attempt.id,
        reading_test_id=attempt.reading_test_id,
        score=attempt.score,
        total_questions=total_questions,
        band_score=float(attempt.band_score),
        submitted_at=attempt.submitted_at,
        answers=answers,
    )

@router.post(
    "/tests/{test_id}/start",
    response_model=ReadingAttemptStartResponse,
)
async def start_reading_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ReadingTest)
        .where(ReadingTest.id == test_id)
    )

    reading_test = result.scalars().first()

    if reading_test is None:
        raise HTTPException(
            status_code=404,
            detail="Reading test not found",
        )

    attempt = ReadingAttempt(
        user_id=current_user_id,
        reading_test_id=test_id,
    )

    db.add(attempt)

    await db.commit()
    await db.refresh(attempt)

    return ReadingAttemptStartResponse(
        attempt_id=attempt.id,
        reading_test_id=attempt.reading_test_id,
        started_at=attempt.started_at,
    )