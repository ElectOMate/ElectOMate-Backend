"""revert_to_country_code_string

Revision ID: b5f6g7h8i9j0
Revises: 515d4443abbb
Create Date: 2025-11-08 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b5f6g7h8i9j0'
down_revision: Union[str, Sequence[str], None] = '515d4443abbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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


def downgrade() -> None:
    """Downgrade schema."""
    # Add country_id column
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

    # Remove country_code column
    op.drop_column('questionnaire_result_table', 'country_code')
