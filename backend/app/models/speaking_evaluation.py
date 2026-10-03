import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.speaking_response import SpeakingResponse


class SpeakingEvaluation(Base):
    __tablename__ = "speaking_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("speaking_responses.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    fluency_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    lexical_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    grammar_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    pronunciation_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    overall_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    improvements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evaluated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    response: Mapped["SpeakingResponse"] = relationship(back_populates="evaluation")
