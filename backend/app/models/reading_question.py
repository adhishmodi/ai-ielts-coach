import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.passage import Passage


class ReadingQuestion(Base):
    __tablename__ = "reading_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    passage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "passages.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    options: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True
    )

    correct_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    passage: Mapped["Passage"] = relationship(
        back_populates="questions"
    )