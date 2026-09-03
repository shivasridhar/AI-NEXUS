"""Merge multiple heads

Revision ID: 6c6bf99d9aa5
Revises: 4e4147dffb26
Create Date: 2026-07-19 16:42:25.007350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c6bf99d9aa5'
down_revision: Union[str, Sequence[str], None] = '4e4147dffb26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
