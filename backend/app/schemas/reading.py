from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class ReadingQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    options: list | None = None
    order: int


class PassageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    order: int
    questions: list[ReadingQuestionResponse]


class ReadingTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    difficulty: str
    time_limit_minutes: int
    passages: list[PassageResponse]

class ReadingAnswerSubmission(BaseModel):
    question_id: UUID
    answer: str


class ReadingSubmissionRequest(BaseModel):
    answers: list[ReadingAnswerSubmission]


class ReadingSubmissionResponse(BaseModel):
    attempt_id: UUID
    score: int
    total_questions: int
    band_score: float

class ReadingAttemptResponse(BaseModel):
    attempt_id: UUID
    reading_test_id: UUID
    score: int | None = None
    total_questions: int
    band_score: float | None = None
    submitted_at: datetime | None = None

class ReadingAnswerDetailResponse(BaseModel):
    question_id: UUID
    question_text: str
    question_type: str
    user_answer: str
    correct_answer: str
    is_correct: bool


class ReadingAttemptDetailResponse(BaseModel):
    attempt_id: UUID
    reading_test_id: UUID
    score: int | None = None
    total_questions: int
    band_score: float | None = None
    submitted_at: datetime | None = None
    answers: list[ReadingAnswerDetailResponse]

class ReadingAttemptStartResponse(BaseModel):
    attempt_id: UUID
    reading_test_id: UUID
    started_at: datetime