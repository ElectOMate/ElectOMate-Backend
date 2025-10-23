"""Fix enum

Revision ID: 130527b089b1
Revises: 614de782e806
Create Date: 2025-10-12 16:40:12.227679
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "130527b089b1"
down_revision: str | Sequence[str] | None = "614de782e806"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ENUM_NAME = "parsingquality"
NEW_ENUM_NAME = f"{OLD_ENUM_NAME}_new"
OLD_ENUM_TEMP = f"{OLD_ENUM_NAME}_old"

old_values = (
    "NO_PARSING",
    "POOR",
    "FAIR",
    "GOOD",
    "EXCELLENT",
    "UNSPECIFIED",
)

new_values = (
    "NO_PARSING",
    "POOR",
    "FAIR",
    "GOOD",
    "EXCELLENT",
    "FAILED",  # <— new value
    "UNSPECIFIED",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Rename the current enum type (e.g. parsingquality -> parsingquality_old)
    op.execute(sa.text(f'ALTER TYPE "{OLD_ENUM_NAME}" RENAME TO "{OLD_ENUM_TEMP}"'))

    # 2. Create the replacement type with the desired values
    sa.Enum(*new_values, name=NEW_ENUM_NAME).create(bind, checkfirst=False)
    op.execute(sa.text(f'ALTER TYPE "{NEW_ENUM_NAME}" RENAME TO "{OLD_ENUM_NAME}"'))

    # 3. Update the column to use the new type
    op.execute(
        sa.text(
            f'ALTER TABLE "document_table" '
            f'ALTER COLUMN "parsing_quality" TYPE "{OLD_ENUM_NAME}" '
            f'USING "parsing_quality"::text::"{OLD_ENUM_NAME}"'
        )
    )

    # 4. Drop the temp enum
    op.execute(sa.text(f'DROP TYPE "{OLD_ENUM_TEMP}"'))


def downgrade() -> None:
    bind = op.get_bind()

    # Reverse the process: rename, recreate old type, cast back, drop temp
    op.execute(sa.text(f'ALTER TYPE "{OLD_ENUM_NAME}" RENAME TO "{OLD_ENUM_TEMP}"'))

    sa.Enum(*old_values, name=NEW_ENUM_NAME).create(bind, checkfirst=False)
    op.execute(sa.text(f'ALTER TYPE "{NEW_ENUM_NAME}" RENAME TO "{OLD_ENUM_NAME}"'))

    op.execute(
        sa.text(
            f'ALTER TABLE "document_table" '
            f'ALTER COLUMN "parsing_quality" TYPE "{OLD_ENUM_NAME}" '
            f'USING "parsing_quality"::text::"{OLD_ENUM_NAME}"'
        )
    )

    # If rows contain values missing in old_values (e.g. FAILED), delete/convert them before downgrade:
    # op.execute(sa.text(
    #     "UPDATE document_table SET parsing_quality = 'NO_PARSING' WHERE parsing_quality = 'FAILED'"
    # ))

    op.execute(sa.text(f'DROP TYPE "{OLD_ENUM_TEMP}"'))
