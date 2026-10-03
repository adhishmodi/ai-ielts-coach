import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.speaking_part import SpeakingPart


class SpeakingTest(Base):
    __tablename__ = "speaking_tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(30), nullable=False, default="academic")
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    parts: Mapped[list["SpeakingPart"]] = relationship(
        back_populates="speaking_test", cascade="all, delete-orphan", order_by="SpeakingPart.order"
    )
