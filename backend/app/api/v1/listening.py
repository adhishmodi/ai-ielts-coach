from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id
from app.database import get_db
from app.models.listening_answer import ListeningAnswer
from app.models.listening_attempt import ListeningAttempt
from app.models.listening_question import ListeningQuestion
from app.models.listening_test import ListeningTest
from app.models.listening_section import ListeningSection
from app.schemas.listening import (
    ListeningAnswerDetailResponse,
    ListeningAttemptDetailResponse,
    ListeningAttemptResponse,
    ListeningAttemptStartResponse,
    ListeningSubmissionRequest,
    ListeningSubmissionResponse,
    ListeningTestResponse,
)
from app.services.listening import (
    calculate_listening_band,
    calculate_listening_score,
    validate_question_type,
)

router = APIRouter(prefix="/listening", tags=["Listening"])


def _question_list(test: ListeningTest) -> list[ListeningQuestion]:
    return [
        question
        for section in test.sections
        for question in section.questions
    ]


@router.get("/tests", response_model=list[ListeningTestResponse])
async def get_listening_tests(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningTest)
        .options(
            selectinload(ListeningTest.sections)
            .selectinload(ListeningSection.questions)
        )
        .order_by(ListeningTest.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/tests/{test_id}", response_model=ListeningTestResponse)
async def get_listening_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningTest)
        .where(ListeningTest.id == test_id)
        .options(
            selectinload(ListeningTest.sections)
            .selectinload(ListeningSection.questions)
        )
    )
    listening_test = result.scalars().unique().first()
    if listening_test is None:
        raise HTTPException(status_code=404, detail="Listening test not found")
    return listening_test


@router.post(
    "/tests/{test_id}/start",
    response_model=ListeningAttemptStartResponse,
)
async def start_listening_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningTest).where(ListeningTest.id == test_id)
    )
    listening_test = result.scalars().first()
    if listening_test is None:
        raise HTTPException(status_code=404, detail="Listening test not found")

    attempt = ListeningAttempt(
        user_id=current_user_id,
        listening_test_id=test_id,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return ListeningAttemptStartResponse(
        attempt_id=attempt.id,
        listening_test_id=attempt.listening_test_id,
        started_at=attempt.started_at,
    )


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=ListeningSubmissionResponse,
)
async def submit_listening_test(
    attempt_id: UUID,
    submission: ListeningSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningAttempt)
        .where(
            ListeningAttempt.id == attempt_id,
            ListeningAttempt.user_id == current_user_id,
        )
        .options(
            selectinload(ListeningAttempt.listening_test)
            .selectinload(ListeningTest.sections)
            .selectinload(ListeningSection.questions)
        )
    )
    attempt = result.scalars().unique().first()

    if attempt is None:
        raise HTTPException(status_code=404, detail="Listening attempt not found")
    if attempt.submitted_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Listening attempt has already been submitted",
        )
    if not submission.answers:
        raise HTTPException(
            status_code=400,
            detail="At least one answer is required",
        )

    questions = _question_list(attempt.listening_test)
    for question in questions:
        if not validate_question_type(question.question_type):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported question type: {question.question_type}",
            )

    question_map = {str(question.id): question for question in questions}
    submitted_answers: dict[str, str] = {}

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
    score = calculate_listening_score(submitted_answers, question_data)
    total_questions = len(questions)
    band_score = calculate_listening_band(score, total_questions)

    attempt.submitted_at = datetime.now(UTC)
    attempt.score = score
    attempt.band_score = band_score

    for question_id, answer in submitted_answers.items():
        db.add(
            ListeningAnswer(
                attempt_id=attempt.id,
                question_id=UUID(question_id),
                answer=answer,
            )
        )

    await db.commit()
    await db.refresh(attempt)

    return ListeningSubmissionResponse(
        attempt_id=attempt.id,
        score=score,
        total_questions=total_questions,
        band_score=float(attempt.band_score),
    )


@router.get(
    "/attempts",
    response_model=list[ListeningAttemptResponse],
)
async def get_listening_attempts(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningAttempt)
        .where(ListeningAttempt.user_id == current_user_id)
        .options(
            selectinload(ListeningAttempt.listening_test)
            .selectinload(ListeningTest.sections)
            .selectinload(ListeningSection.questions)
        )
        .order_by(ListeningAttempt.submitted_at.desc())
    )
    attempts = result.scalars().unique().all()

    return [
        ListeningAttemptResponse(
            attempt_id=attempt.id,
            listening_test_id=attempt.listening_test_id,
            score=attempt.score,
            total_questions=sum(
                len(section.questions)
                for section in attempt.listening_test.sections
            ),
            band_score=(
                float(attempt.band_score)
                if attempt.band_score is not None
                else None
            ),
            submitted_at=attempt.submitted_at,
        )
        for attempt in attempts
    ]


@router.get(
    "/attempts/{attempt_id}",
    response_model=ListeningAttemptDetailResponse,
)
async def get_listening_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ListeningAttempt)
        .where(
            ListeningAttempt.id == attempt_id,
            ListeningAttempt.user_id == current_user_id,
        )
        .options(
            selectinload(ListeningAttempt.answers)
            .selectinload(ListeningAnswer.question),
            selectinload(ListeningAttempt.listening_test)
            .selectinload(ListeningTest.sections)
            .selectinload(ListeningSection.questions),
        )
    )
    attempt = result.scalars().unique().first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Listening attempt not found")

    answers = [
        ListeningAnswerDetailResponse(
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
        len(section.questions) for section in attempt.listening_test.sections
    )

    return ListeningAttemptDetailResponse(
        attempt_id=attempt.id,
        listening_test_id=attempt.listening_test_id,
        score=attempt.score,
        total_questions=total_questions,
        band_score=(
            float(attempt.band_score)
            if attempt.band_score is not None
            else None
        ),
        submitted_at=attempt.submitted_at,
        answers=answers,
    )
