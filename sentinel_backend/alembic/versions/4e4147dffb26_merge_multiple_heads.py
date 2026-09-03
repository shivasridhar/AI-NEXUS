"""Merge multiple heads

Revision ID: 4e4147dffb26
Revises: ab2cf4492ad0, d5e8f1a2b3c4
Create Date: 2026-07-19 11:17:11.443104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e4147dffb26'
down_revision: Union[str, Sequence[str], None] = ('ab2cf4492ad0', 'd5e8f1a2b3c4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
