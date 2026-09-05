"""añade reports.etiquetas

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04 19:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: los informes ya almacenados no tienen etiquetas, y los clientes
    # antiguos siguen enviando payloads sin ese campo.
    op.add_column('reports', sa.Column('etiquetas', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'etiquetas')
