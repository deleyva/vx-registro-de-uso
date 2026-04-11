"""rename migrasfreeCid to migasfreeCid

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column
    op.alter_column(
        'reports',
        'migrasfreeCid',
        new_column_name='migasfreeCid',
    )
    # Rename index
    op.drop_index('reports_migrasfreeCid_idx', table_name='reports')
    op.create_index('reports_migasfreeCid_idx', 'reports', ['migasfreeCid'], unique=False)


def downgrade() -> None:
    # Revert index
    op.drop_index('reports_migasfreeCid_idx', table_name='reports')
    op.create_index('reports_migrasfreeCid_idx', 'reports', ['migrasfreeCid'], unique=False)
    # Revert column
    op.alter_column(
        'reports',
        'migasfreeCid',
        new_column_name='migrasfreeCid',
    )
