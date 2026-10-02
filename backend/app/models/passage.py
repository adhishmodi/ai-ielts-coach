import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.reading_test import ReadingTest
    from app.models.reading_question import ReadingQuestion


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    reading_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "reading_tests.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    reading_test: Mapped["ReadingTest"] = relationship(
        back_populates="passages"
    )

    questions: Mapped[list["ReadingQuestion"]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        order_by="ReadingQuestion.order"
    )