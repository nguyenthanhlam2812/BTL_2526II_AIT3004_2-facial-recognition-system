"""admin users and system settings

Revision ID: 9a7f0f4d4f2a
Revises: ff405d862c85
Create Date: 2026-05-11 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7f0f4d4f2a"
down_revision: Union[str, None] = "ff405d862c85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.execute("UPDATE users SET role = 'owner' WHERE role = 'admin'")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
        server_default="owner",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
        server_default="admin",
        existing_nullable=False,
    )
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'owner'")
    op.drop_table("system_settings")
