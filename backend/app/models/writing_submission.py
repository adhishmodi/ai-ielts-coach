import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.writing_attempt import WritingAttempt
    from app.models.writing_task import WritingTask
    from app.models.writing_evaluation import WritingEvaluation


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"
    __table_args__ = (UniqueConstraint("attempt_id", "task_id", name="uq_writing_submission_task"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    attempt: Mapped["WritingAttempt"] = relationship(back_populates="submissions")
    task: Mapped["WritingTask"] = relationship(back_populates="submissions")
    evaluation: Mapped["WritingEvaluation | None"] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )
