"""add media url columns for marketplace products

Revision ID: 20260530_0008
Revises: 20260530_0007
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0008"
down_revision = "20260530_0007"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_name in _table_names() and column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if table_name in _table_names() and column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing(
        "marketplace_products",
        sa.Column("image_urls_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    _add_column_if_missing(
        "marketplace_products",
        sa.Column("video_urls_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    _drop_column_if_exists("marketplace_products", "video_urls_json")
    _drop_column_if_exists("marketplace_products", "image_urls_json")

