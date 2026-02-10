"""add_source_level_to_overlays

Revision ID: c97521d7a70c
Revises: acda00a0a4a6
Create Date: 2026-02-11 03:54:27.797380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c97521d7a70c'
down_revision: Union[str, None] = 'acda00a0a4a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename layer column to source_level (layer conflicts with layer relationship)
    op.alter_column('overlays', 'layer', new_column_name='source_level')


def downgrade() -> None:
    op.alter_column('overlays', 'source_level', new_column_name='layer')
