"""analytics product facts

Revision ID: 20260530_0005
Revises: 20260530_0004
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0005"
down_revision = "20260530_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "analytics_product_facts" not in table_names:
        op.create_table(
            "analytics_product_facts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("sku", sa.String(length=80), nullable=False),
            sa.Column("brand", sa.String(length=120), nullable=False),
            sa.Column("category", sa.String(length=120), nullable=False),
            sa.Column("warehouse", sa.String(length=120), nullable=True),
            sa.Column("orders_count", sa.Integer(), nullable=False),
            sa.Column("revenue_amount", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("analytics_product_facts")}
    if "ix_analytics_product_facts_team_id" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_team_id"), "analytics_product_facts", ["team_id"], unique=False)
    if "ix_analytics_product_facts_connection_id" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_connection_id"), "analytics_product_facts", ["connection_id"], unique=False)
    if "ix_analytics_product_facts_sku" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_sku"), "analytics_product_facts", ["sku"], unique=False)
    if "ix_analytics_product_facts_brand" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_brand"), "analytics_product_facts", ["brand"], unique=False)
    if "ix_analytics_product_facts_category" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_category"), "analytics_product_facts", ["category"], unique=False)
    if "ix_analytics_product_facts_warehouse" not in indexes:
        op.create_index(op.f("ix_analytics_product_facts_warehouse"), "analytics_product_facts", ["warehouse"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "analytics_product_facts" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("analytics_product_facts")}
    if "ix_analytics_product_facts_warehouse" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_warehouse"), table_name="analytics_product_facts")
    if "ix_analytics_product_facts_category" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_category"), table_name="analytics_product_facts")
    if "ix_analytics_product_facts_brand" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_brand"), table_name="analytics_product_facts")
    if "ix_analytics_product_facts_sku" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_sku"), table_name="analytics_product_facts")
    if "ix_analytics_product_facts_connection_id" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_connection_id"), table_name="analytics_product_facts")
    if "ix_analytics_product_facts_team_id" in indexes:
        op.drop_index(op.f("ix_analytics_product_facts_team_id"), table_name="analytics_product_facts")
    op.drop_table("analytics_product_facts")
