import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.listening_test import ListeningTest
    from app.models.listening_question import ListeningQuestion


class ListeningSection(Base):
    __tablename__ = "listening_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listening_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listening_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    listening_test: Mapped["ListeningTest"] = relationship(
        back_populates="sections"
    )
    questions: Mapped[list["ListeningQuestion"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ListeningQuestion.order",
    )
