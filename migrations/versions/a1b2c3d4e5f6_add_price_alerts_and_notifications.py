"""add_price_alerts_and_notifications

Revision ID: a1b2c3d4e5f6
Revises: 03fc22ea9ca6
Create Date: 2026-02-25 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '03fc22ea9ca6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria as tabelas price_alerts e user_notifications se não existirem."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "price_alerts" not in existing_tables:
        op.create_table(
            "price_alerts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("item_id", sa.String, nullable=False, index=True),
            sa.Column("display_name", sa.String, nullable=True),
            sa.Column("city", sa.String, nullable=True),
            sa.Column("quality", sa.Integer, nullable=True),
            # regra absoluta
            sa.Column("target_price", sa.Float, nullable=True),
            # regra percentual manual
            sa.Column("expected_price", sa.Float, nullable=True),
            sa.Column("percent_below", sa.Float, nullable=True),
            # IA
            sa.Column("use_ai_expected", sa.Boolean, default=True),
            sa.Column("ai_days", sa.Integer, default=7),
            sa.Column("ai_resolution", sa.String, default="6h"),
            sa.Column("ai_stat", sa.String, default="median"),
            sa.Column("ai_min_points", sa.Integer, default=10),
            # cache do último preço esperado calculado pela IA
            sa.Column("last_expected_price", sa.Float, nullable=True),
            sa.Column(
                "last_expected_at", sa.DateTime(timezone=True), nullable=True
            ),
            # anti-spam
            sa.Column("cooldown_minutes", sa.Integer, default=60),
            sa.Column(
                "last_triggered_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("is_active", sa.Boolean, default=True),
        )

    if "user_notifications" not in existing_tables:
        op.create_table(
            "user_notifications",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("title", sa.String, nullable=False),
            sa.Column("body", sa.String, nullable=False),
            sa.Column("is_read", sa.Boolean, default=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )


def downgrade() -> None:
    """Remove as tabelas criadas por esta migration."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "user_notifications" in existing_tables:
        op.drop_table("user_notifications")

    if "price_alerts" in existing_tables:
        op.drop_table("price_alerts")
