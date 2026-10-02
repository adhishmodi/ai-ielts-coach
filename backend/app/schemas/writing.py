from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WritingTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_number: int
    task_type: str
    prompt: str
    instructions: str | None = None
    minimum_words: int
    order: int


class WritingTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    test_type: str
    difficulty: str
    time_limit_minutes: int
    tasks: list[WritingTaskResponse]


class WritingAttemptStartResponse(BaseModel):
    attempt_id: UUID
    writing_test_id: UUID
    started_at: datetime
    status: str


class WritingDraftRequest(BaseModel):
    response_text: str = Field(default="", max_length=50000)


class WritingDraftResponse(BaseModel):
    submission_id: UUID
    attempt_id: UUID
    task_id: UUID
    response_text: str
    word_count: int
    minimum_words: int
    below_minimum_words: bool
    submitted_at: datetime


class WritingSubmitResponse(BaseModel):
    attempt_id: UUID
    status: str
    submitted_at: datetime
    task_word_counts: dict[str, int]
    below_minimum_tasks: list[int]


class WritingEvaluateResponse(BaseModel):
    submission_id: UUID
    status: str
    evaluation: "WritingEvaluationResponse"


class WritingEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_response_band: float | None = None
    task_achievement_band: float | None = None
    coherence_band: float | None = None
    lexical_band: float | None = None
    grammar_band: float | None = None
    overall_band: float | None = None
    feedback: str | None = None
    strengths: list | None = None
    improvements: list | None = None
    evaluated_by: str
    evaluated_at: datetime


class WritingSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    response_text: str
    word_count: int
    submitted_at: datetime
    evaluation: WritingEvaluationResponse | None = None


class WritingAttemptResponse(BaseModel):
    attempt_id: UUID
    writing_test_id: UUID
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    overall_band: float | None = None


class WritingAttemptDetailResponse(WritingAttemptResponse):
    submissions: list[WritingSubmissionResponse]
