import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.writing_submission import WritingSubmission


class WritingEvaluation(Base):
    __tablename__ = "writing_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_submissions.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )
    task_response_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    task_achievement_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    coherence_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    lexical_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    grammar_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    overall_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    improvements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evaluated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    submission: Mapped["WritingSubmission"] = relationship(
        back_populates="evaluation", primaryjoin="WritingEvaluation.submission_id == WritingSubmission.id"
    )
