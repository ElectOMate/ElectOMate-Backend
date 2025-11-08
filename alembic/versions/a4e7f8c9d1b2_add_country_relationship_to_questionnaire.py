"""add_country_relationship_to_questionnaire

Revision ID: a4e7f8c9d1b2
Revises: 3525046c8b4b
Create Date: 2025-11-08 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a4e7f8c9d1b2'
down_revision: Union[str, Sequence[str], None] = '3525046c8b4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add country_id column to questionnaire_result_table
    op.add_column('questionnaire_result_table',
        sa.Column('country_id', sa.Uuid(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'questionnaire_result_table_country_id_fkey',
        'questionnaire_result_table',
        'country_table',
        ['country_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Remove old country_code column
    op.drop_column('questionnaire_result_table', 'country_code')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back country_code column
    op.add_column('questionnaire_result_table',
        sa.Column('country_code', sa.String(), nullable=True)
    )

    # Remove foreign key constraint
    op.drop_constraint(
        'questionnaire_result_table_country_id_fkey',
        'questionnaire_result_table',
        type_='foreignkey'
    )

    # Remove country_id column
    op.drop_column('questionnaire_result_table', 'country_id')
