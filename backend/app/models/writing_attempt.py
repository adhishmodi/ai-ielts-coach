import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.writing_test import WritingTest
    from app.models.writing_submission import WritingSubmission
    from app.models.user import User


class WritingAttempt(Base):
    __tablename__ = "writing_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    writing_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    overall_band: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)

    user: Mapped["User"] = relationship()
    writing_test: Mapped["WritingTest"] = relationship()
    submissions: Mapped[list["WritingSubmission"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", order_by="WritingSubmission.submitted_at"
    )
