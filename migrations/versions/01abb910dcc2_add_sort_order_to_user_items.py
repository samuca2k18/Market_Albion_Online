"""add sort_order to user_items

Revision ID: 01abb910dcc2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-06 05:28:12.135311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01abb910dcc2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_items",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("user_items", "sort_order", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_items", "sort_order")
