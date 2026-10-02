import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.reading_test import ReadingTest
    from app.models.user import User
    from app.models.reading_answer import ReadingAnswer


class ReadingAttempt(Base):
    __tablename__ = "reading_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reading_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reading_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    band_score: Mapped[float | None] = mapped_column(
        Numeric(2, 1),
        nullable=True,
    )

    user: Mapped["User"] = relationship()
    reading_test: Mapped["ReadingTest"] = relationship()
    answers: Mapped[list["ReadingAnswer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ReadingAnswer.created_at",
    )