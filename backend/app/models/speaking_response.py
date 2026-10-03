import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.speaking_attempt import SpeakingAttempt
    from app.models.speaking_part import SpeakingPart
    from app.models.speaking_evaluation import SpeakingEvaluation


class SpeakingResponse(Base):
    __tablename__ = "speaking_responses"
    __table_args__ = (
        UniqueConstraint("attempt_id", "part_id", name="uq_speaking_response_part"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("speaking_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("speaking_parts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    attempt: Mapped["SpeakingAttempt"] = relationship(back_populates="responses")
    part: Mapped["SpeakingPart"] = relationship(back_populates="responses")
    evaluation: Mapped["SpeakingEvaluation | None"] = relationship(
        back_populates="response", cascade="all, delete-orphan", uselist=False
    )
