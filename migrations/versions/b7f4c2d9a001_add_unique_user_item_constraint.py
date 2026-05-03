"""add unique constraint for user_items user_id + item_name

Revision ID: b7f4c2d9a001
Revises: 01abb910dcc2
Create Date: 2026-04-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7f4c2d9a001"
down_revision: Union[str, Sequence[str], None] = "01abb910dcc2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DELETE FROM user_items
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, item_name
                        ORDER BY id
                    ) AS rn
                FROM user_items
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )
    op.create_index(
        "uq_user_items_user_item_name",
        "user_items",
        ["user_id", "item_name"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_user_items_user_item_name", table_name="user_items")
