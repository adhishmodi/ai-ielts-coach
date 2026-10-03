from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SpeakingPartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    part_number: int
    title: str
    instructions: str | None
    prompt: str
    preparation_seconds: int
    response_seconds: int
    order: int


class SpeakingTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    test_type: str
    difficulty: str
    time_limit_minutes: int
    created_at: datetime
    parts: list[SpeakingPartResponse]


class SpeakingAttemptStartResponse(BaseModel):
    attempt_id: UUID
    speaking_test_id: UUID
    started_at: datetime
    status: str


class SpeakingDraftRequest(BaseModel):
    transcript: str = Field(min_length=1)
    audio_url: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class SpeakingDraftResponse(BaseModel):
    response_id: UUID
    attempt_id: UUID
    part_id: UUID
    transcript: str
    audio_url: str | None
    duration_seconds: int | None
    submitted_at: datetime


class SpeakingSubmitResponse(BaseModel):
    attempt_id: UUID
    status: str
    submitted_at: datetime
    missing_parts: list[int]


class SpeakingEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    response_id: UUID
    fluency_band: float | None
    lexical_band: float | None
    grammar_band: float | None
    pronunciation_band: float | None
    overall_band: float | None
    feedback: str | None
    strengths: list | None
    improvements: list | None
    evaluated_by: str
    evaluated_at: datetime


class SpeakingResponseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    part_id: UUID
    transcript: str
    audio_url: str | None
    duration_seconds: int | None
    submitted_at: datetime
    evaluation: SpeakingEvaluationResponse | None = None


class SpeakingAttemptResponse(BaseModel):
    attempt_id: UUID
    speaking_test_id: UUID
    status: str
    started_at: datetime
    submitted_at: datetime | None
    overall_band: float | None


class SpeakingAttemptDetailResponse(BaseModel):
    attempt_id: UUID
    speaking_test_id: UUID
    status: str
    started_at: datetime
    submitted_at: datetime | None
    overall_band: float | None
    responses: list[SpeakingResponseDetail]


class SpeakingEvaluateResponse(BaseModel):
    response_id: UUID
    status: str
    evaluation: SpeakingEvaluationResponse
