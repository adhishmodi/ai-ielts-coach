from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListeningQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    options: list | None = None
    order: int


class ListeningSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    instructions: str | None = None
    audio_url: str | None = None
    order: int
    questions: list[ListeningQuestionResponse]


class ListeningTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    difficulty: str
    time_limit_minutes: int
    sections: list[ListeningSectionResponse]


class ListeningAnswerSubmission(BaseModel):
    question_id: UUID
    answer: str


class ListeningSubmissionRequest(BaseModel):
    answers: list[ListeningAnswerSubmission]


class ListeningSubmissionResponse(BaseModel):
    attempt_id: UUID
    score: int
    total_questions: int
    band_score: float


class ListeningAttemptResponse(BaseModel):
    attempt_id: UUID
    listening_test_id: UUID
    score: int | None = None
    total_questions: int
    band_score: float | None = None
    submitted_at: datetime | None = None


class ListeningAnswerDetailResponse(BaseModel):
    question_id: UUID
    question_text: str
    question_type: str
    user_answer: str
    correct_answer: str
    is_correct: bool


class ListeningAttemptDetailResponse(BaseModel):
    attempt_id: UUID
    listening_test_id: UUID
    score: int | None = None
    total_questions: int
    band_score: float | None = None
    submitted_at: datetime | None = None
    answers: list[ListeningAnswerDetailResponse]


class ListeningAttemptStartResponse(BaseModel):
    attempt_id: UUID
    listening_test_id: UUID
    started_at: datetime
