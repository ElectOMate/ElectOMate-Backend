"""replace quiz_result country_id with country_code

Revision ID: c6d7e8f9g0h1
Revises: b5f6g7h8i9j0
Create Date: 2025-11-08 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9g0h1'
down_revision: Union[str, Sequence[str], None] = 'b5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - replace country_id foreign key with country_code string."""
    # Add country_code column
    op.add_column('quiz_result_table',
        sa.Column('country_code', sa.String(), nullable=True)
    )

    # Drop foreign key constraint first
    op.drop_constraint(
        'quiz_result_table_country_id_fkey',
        'quiz_result_table',
        type_='foreignkey'
    )

    # Drop country_id column
    op.drop_column('quiz_result_table', 'country_id')


def downgrade() -> None:
    """Downgrade schema - revert back to country_id foreign key."""
    # Add country_id column back
    op.add_column('quiz_result_table',
        sa.Column('country_id', postgresql.UUID(), nullable=True)
    )

    # Re-create foreign key constraint
    op.create_foreign_key(
        'quiz_result_table_country_id_fkey',
        'quiz_result_table',
        'country_table',
        ['country_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Remove country_code column
    op.drop_column('quiz_result_table', 'country_code')
