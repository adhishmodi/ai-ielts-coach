import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.speaking_test import SpeakingTest
    from app.models.speaking_response import SpeakingResponse


class SpeakingPart(Base):
    __tablename__ = "speaking_parts"
    __table_args__ = (
        UniqueConstraint("speaking_test_id", "part_number", name="uq_speaking_part_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    speaking_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("speaking_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    preparation_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    speaking_test: Mapped["SpeakingTest"] = relationship(back_populates="parts")
    responses: Mapped[list["SpeakingResponse"]] = relationship(back_populates="part")
