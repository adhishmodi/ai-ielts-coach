import uuid
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.passage import Passage


class ReadingTest(Base):
    __tablename__ = "reading_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium"
    )

    time_limit_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=60
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    passages: Mapped[list["Passage"]] = relationship(
        back_populates="reading_test",
        cascade="all, delete-orphan",
        order_by="Passage.order"
    )