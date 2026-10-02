"""add reading module

Revision ID: 86a4df320dd0
Revises: 910f6063a840
Create Date: 2026-09-06 20:47:22.293619
"""

from typing import Sequence, Union

from alembic import op


revision: str = "86a4df320dd0"
down_revision: Union[str, Sequence[str], None] = "910f6063a840"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass