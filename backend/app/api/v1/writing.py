from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id
from app.database import get_db
from app.models.writing_attempt import WritingAttempt
from app.models.writing_evaluation import WritingEvaluation
from app.models.writing_submission import WritingSubmission
from app.models.writing_task import WritingTask
from app.models.writing_test import WritingTest
from app.schemas.writing import (
    WritingAttemptDetailResponse,
    WritingAttemptResponse,
    WritingAttemptStartResponse,
    WritingDraftRequest,
    WritingDraftResponse,
    WritingSubmitResponse,
    WritingEvaluateResponse,
    WritingTestResponse,
)
from app.services.writing import GeminiWritingEvaluator, calculate_writing_overall_band, count_words
from app.config import settings

router = APIRouter(prefix="/writing", tags=["Writing"])


async def _owned_attempt(
    db: AsyncSession, attempt_id: UUID, user_id: str
) -> WritingAttempt | None:
    result = await db.execute(
        select(WritingAttempt)
        .where(WritingAttempt.id == attempt_id, WritingAttempt.user_id == user_id)
        .options(
            selectinload(WritingAttempt.writing_test).selectinload(WritingTest.tasks),
            selectinload(WritingAttempt.submissions).selectinload(WritingSubmission.task),
            selectinload(WritingAttempt.submissions).selectinload(WritingSubmission.evaluation),
        )
    )
    return result.scalars().unique().first()


@router.get("/tests", response_model=list[WritingTestResponse])
async def get_writing_tests(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WritingTest)
        .options(selectinload(WritingTest.tasks))
        .order_by(WritingTest.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/tests/{test_id}", response_model=WritingTestResponse)
async def get_writing_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WritingTest)
        .where(WritingTest.id == test_id)
        .options(selectinload(WritingTest.tasks))
    )
    writing_test = result.scalars().unique().first()
    if writing_test is None:
        raise HTTPException(status_code=404, detail="Writing test not found")
    return writing_test


@router.post("/tests/{test_id}/start", response_model=WritingAttemptStartResponse)
async def start_writing_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WritingTest).where(WritingTest.id == test_id).options(selectinload(WritingTest.tasks))
    )
    writing_test = result.scalars().unique().first()
    if writing_test is None:
        raise HTTPException(status_code=404, detail="Writing test not found")
    if not writing_test.tasks:
        raise HTTPException(status_code=400, detail="Writing test has no tasks")

    attempt = WritingAttempt(user_id=current_user_id, writing_test_id=test_id)
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return WritingAttemptStartResponse(
        attempt_id=attempt.id,
        writing_test_id=attempt.writing_test_id,
        started_at=attempt.started_at,
        status=attempt.status,
    )


@router.put(
    "/attempts/{attempt_id}/tasks/{task_id}",
    response_model=WritingDraftResponse,
)
async def save_writing_draft(
    attempt_id: UUID,
    task_id: UUID,
    draft: WritingDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Writing attempt not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Writing attempt is no longer editable")

    task = next((task for task in attempt.writing_test.tasks if task.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=400, detail="Task does not belong to this writing test")

    submission = next((item for item in attempt.submissions if item.task_id == task_id), None)
    if submission is None:
        submission = WritingSubmission(
            attempt_id=attempt.id,
            task_id=task.id,
            response_text=draft.response_text,
            word_count=count_words(draft.response_text),
        )
        db.add(submission)
    else:
        submission.response_text = draft.response_text
        submission.word_count = count_words(draft.response_text)
        submission.submitted_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(submission)
    return WritingDraftResponse(
        submission_id=submission.id,
        attempt_id=attempt.id,
        task_id=task.id,
        response_text=submission.response_text,
        word_count=submission.word_count,
        minimum_words=task.minimum_words,
        below_minimum_words=submission.word_count < task.minimum_words,
        submitted_at=submission.submitted_at,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=WritingSubmitResponse)
async def submit_writing_test(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Writing attempt not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Writing attempt has already been submitted")

    tasks = attempt.writing_test.tasks
    submissions_by_task = {submission.task_id: submission for submission in attempt.submissions}
    missing = [task.task_number for task in tasks if task.id not in submissions_by_task]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"All writing tasks must be answered before submission. Missing tasks: {missing}",
        )

    now = datetime.now(UTC)
    attempt.submitted_at = now
    attempt.status = "submitted"
    task_word_counts = {
        str(task.task_number): submissions_by_task[task.id].word_count for task in tasks
    }
    below_minimum_tasks = [
        task.task_number
        for task in tasks
        if submissions_by_task[task.id].word_count < task.minimum_words
    ]
    await db.commit()
    await db.refresh(attempt)
    return WritingSubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        task_word_counts=task_word_counts,
        below_minimum_tasks=below_minimum_tasks,
    )


@router.get("/attempts", response_model=list[WritingAttemptResponse])
async def get_writing_attempts(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WritingAttempt)
        .where(WritingAttempt.user_id == current_user_id)
        .order_by(WritingAttempt.started_at.desc())
    )
    attempts = result.scalars().all()
    return [
        WritingAttemptResponse(
            attempt_id=item.id,
            writing_test_id=item.writing_test_id,
            status=item.status,
            started_at=item.started_at,
            submitted_at=item.submitted_at,
            overall_band=float(item.overall_band) if item.overall_band is not None else None,
        )
        for item in attempts
    ]


@router.get("/attempts/{attempt_id}", response_model=WritingAttemptDetailResponse)
async def get_writing_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    attempt = await _owned_attempt(db, attempt_id, current_user_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Writing attempt not found")

    return WritingAttemptDetailResponse(
        attempt_id=attempt.id,
        writing_test_id=attempt.writing_test_id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        overall_band=float(attempt.overall_band) if attempt.overall_band is not None else None,
        submissions=attempt.submissions,
    )

@router.post("/submissions/{submission_id}/evaluate", response_model=WritingEvaluateResponse)
async def evaluate_writing_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WritingSubmission)
        .join(WritingAttempt, WritingAttempt.id == WritingSubmission.attempt_id)
        .where(WritingSubmission.id == submission_id, WritingAttempt.user_id == current_user_id)
        .options(selectinload(WritingSubmission.task), selectinload(WritingSubmission.evaluation), selectinload(WritingSubmission.attempt))
    )
    submission = result.scalars().first()
    if submission is None:
        raise HTTPException(status_code=404, detail="Writing submission not found")
    if submission.attempt.status == "in_progress":
        raise HTTPException(status_code=400, detail="Submit the writing attempt before evaluation")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI evaluation is not configured")
    evaluator = GeminiWritingEvaluator(settings.gemini_api_key, settings.gemini_model)
    try:
        evaluated = await evaluator.evaluate(submission.response_text, submission.task.prompt, submission.task.task_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI evaluation failed: {exc}") from exc
    evaluation = submission.evaluation
    if evaluation is None:
        evaluation = WritingEvaluation(submission_id=submission.id)
        db.add(evaluation)
    evaluation.task_response_band = evaluated.task_response_band
    evaluation.task_achievement_band = evaluated.task_achievement_band
    evaluation.coherence_band = evaluated.coherence_band
    evaluation.lexical_band = evaluated.lexical_band
    evaluation.grammar_band = evaluated.grammar_band
    evaluation.overall_band = evaluated.overall_band
    evaluation.feedback = evaluated.feedback
    evaluation.strengths = evaluated.strengths
    evaluation.improvements = evaluated.improvements
    evaluation.evaluated_by = evaluated.evaluated_by
    evaluation.evaluated_at = datetime.now(UTC)
    all_evaluated = all(item.evaluation is not None for item in submission.attempt.submissions)
    if all_evaluated:
        evaluated_submissions = submission.attempt.submissions
        by_number = {item.task.task_number: item for item in evaluated_submissions}
        if 1 in by_number and 2 in by_number and by_number[1].evaluation and by_number[2].evaluation:
            task1_band = float(by_number[1].evaluation.overall_band)
            task2_band = float(by_number[2].evaluation.overall_band)
            submission.attempt.overall_band = calculate_writing_overall_band(task1_band, task2_band)
        submission.attempt.status = "evaluated"
    await db.commit()
    await db.refresh(evaluation)
    return WritingEvaluateResponse(submission_id=submission.id, status=submission.attempt.status, evaluation=evaluation)