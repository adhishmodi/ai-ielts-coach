import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.listening_test import ListeningTest
    from app.models.listening_answer import ListeningAnswer
    from app.models.user import User


class ListeningAttempt(Base):
    __tablename__ = "listening_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listening_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listening_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band_score: Mapped[float | None] = mapped_column(
        Numeric(2, 1), nullable=True
    )

    user: Mapped["User"] = relationship()
    listening_test: Mapped["ListeningTest"] = relationship()
    answers: Mapped[list["ListeningAnswer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ListeningAnswer.created_at",
    )
