"""ai generation logs

Revision ID: 20260530_0009
Revises: 20260530_0008
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0009"
down_revision = "20260530_0008"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    if table_name not in _table_names():
        return set()
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if table_name in _table_names() and index_name not in _index_names(table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    if "ai_generation_logs" not in _table_names():
        op.create_table(
            "ai_generation_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("connection_id", sa.Integer(), nullable=True),
            sa.Column("product_row_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("operation", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("model_text", sa.String(length=120), nullable=True),
            sa.Column("model_vision", sa.String(length=120), nullable=True),
            sa.Column("model_image", sa.String(length=120), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), nullable=False),
            sa.Column("total_tokens", sa.Integer(), nullable=False),
            sa.Column("cached_input_tokens", sa.Integer(), nullable=False),
            sa.Column("reasoning_tokens", sa.Integer(), nullable=False),
            sa.Column("image_count", sa.Integer(), nullable=False),
            sa.Column("output_asset_count", sa.Integer(), nullable=False),
            sa.Column("estimated_cost_microusd", sa.Integer(), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("trace_id", sa.String(length=120), nullable=True),
            sa.Column("request_json", sa.JSON(), nullable=True),
            sa.Column("response_json", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["product_row_id"], ["marketplace_products.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_ai_generation_logs_team_id", "ai_generation_logs", ["team_id"])
    _create_index_if_missing("ix_ai_generation_logs_connection_id", "ai_generation_logs", ["connection_id"])
    _create_index_if_missing("ix_ai_generation_logs_product_row_id", "ai_generation_logs", ["product_row_id"])
    _create_index_if_missing("ix_ai_generation_logs_user_id", "ai_generation_logs", ["user_id"])
    _create_index_if_missing("ix_ai_generation_logs_provider", "ai_generation_logs", ["provider"])
    _create_index_if_missing("ix_ai_generation_logs_operation", "ai_generation_logs", ["operation"])
    _create_index_if_missing("ix_ai_generation_logs_status", "ai_generation_logs", ["status"])
    _create_index_if_missing("ix_ai_generation_logs_trace_id", "ai_generation_logs", ["trace_id"])
    _create_index_if_missing("ix_ai_generation_logs_created_at", "ai_generation_logs", ["created_at"])


def downgrade() -> None:
    if "ai_generation_logs" in _table_names():
        op.drop_table("ai_generation_logs")
