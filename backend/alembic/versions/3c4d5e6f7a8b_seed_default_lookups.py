"""seed default department and position lookups

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-05-21 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.app.default_lookups import DEFAULT_DEPARTMENTS, DEFAULT_POSITIONS


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


departments_table = sa.table(
    "departments",
    sa.column("name", sa.String(length=64)),
)

positions_table = sa.table(
    "positions",
    sa.column("name", sa.String(length=64)),
)


def upgrade() -> None:
    _insert_missing_names(departments_table, DEFAULT_DEPARTMENTS)
    _insert_missing_names(positions_table, DEFAULT_POSITIONS)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        positions_table.delete().where(positions_table.c.name.in_(DEFAULT_POSITIONS))
    )
    connection.execute(
        departments_table.delete().where(departments_table.c.name.in_(DEFAULT_DEPARTMENTS))
    )


def _insert_missing_names(
    table: sa.TableClause,
    names: tuple[str, ...],
) -> None:
    connection = op.get_bind()
    existing = set(connection.execute(sa.select(table.c.name)).scalars())
    rows = [{"name": name} for name in names if name not in existing]
    if rows:
        op.bulk_insert(table, rows)
