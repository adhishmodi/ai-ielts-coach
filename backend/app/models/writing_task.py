import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.writing_test import WritingTest
    from app.models.writing_submission import WritingSubmission


class WritingTask(Base):
    __tablename__ = "writing_tasks"
    __table_args__ = (UniqueConstraint("writing_test_id", "task_number", name="uq_writing_task_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    writing_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_number: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum_words: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    writing_test: Mapped["WritingTest"] = relationship(back_populates="tasks")
    submissions: Mapped[list["WritingSubmission"]] = relationship(back_populates="task")
