"""añade reports.hostname

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01 11:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: los informes ya almacenados no traen el nombre del equipo, y los
    # clientes anteriores a la 1.0.28 siguen enviando payloads sin ese campo.
    op.add_column('reports', sa.Column('hostname', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'hostname')
