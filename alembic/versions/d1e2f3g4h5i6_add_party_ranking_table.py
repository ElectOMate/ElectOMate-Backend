"""add party_ranking_table for storing questionnaire results rankings

Revision ID: d1e2f3g4h5i6
Revises: c6d7e8f9g0h1
Create Date: 2025-11-08 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, Sequence[str], None] = 'c6d7e8f9g0h1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add party_ranking_table."""
    op.create_table(
        'party_ranking_table',
        sa.Column('party_short_name', sa.String(), nullable=False),
        sa.Column('party_full_name', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('questionnaire_result_id', postgresql.UUID(), nullable=False),
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['questionnaire_result_id'],
            ['questionnaire_result_table.id'],
            name='party_ranking_table_questionnaire_result_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name='party_ranking_table_pkey')
    )


def downgrade() -> None:
    """Downgrade schema - drop party_ranking_table."""
    op.drop_table('party_ranking_table')
