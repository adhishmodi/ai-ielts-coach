"""add listening section audio URL

Revision ID: add_listening_section_audio
Revises: add_speaking_module
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_listening_section_audio"
down_revision: Union[str, Sequence[str], None] = "add_speaking_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listening_sections",
        sa.Column("audio_url", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listening_sections", "audio_url")
