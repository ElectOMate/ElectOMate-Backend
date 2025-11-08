"""drop unused quiz_question and quiz_submission tables

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2025-11-08 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unused quiz_submission_table and quiz_question_table.

    These tables were never used in the application. The actual quiz system uses:
    - quiz_result_table (for quiz submissions)
    - quiz_result_answer_table (for individual answers)
    """
    # Drop quiz_submission_table first (it has FK to quiz_question_table)
    op.drop_table('quiz_submission_table')

    # Drop quiz_question_table
    op.drop_table('quiz_question_table')


def downgrade() -> None:
    """Recreate the unused tables if needed for rollback."""

    # Recreate quiz_question_table
    op.create_table(
        'quiz_question_table',
        sa.Column('question', sa.String(), nullable=False),
        sa.Column('option_a', sa.String(), nullable=False),
        sa.Column('option_b', sa.String(), nullable=False),
        sa.Column('option_c', sa.String(), nullable=False),
        sa.Column('option_d', sa.String(), nullable=False),
        sa.Column('correct_answer', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('country_id', postgresql.UUID(), nullable=True),
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['country_id'], ['country_table.id'], ondelete='SET NULL')
    )

    # Recreate quiz_submission_table
    op.create_table(
        'quiz_submission_table',
        sa.Column('selected_option', sa.Integer(), nullable=False),
        sa.Column('question_id', postgresql.UUID(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['question_id'], ['quiz_question_table.id'], ondelete='CASCADE')
    )
