"""reconcile baseline schema on environments without alembic history

Revision ID: 20260530_0004
Revises: 20260530_0003
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0004"
down_revision = "20260530_0003"
branch_labels = None
depends_on = None


def _has_column(columns: list[dict], name: str) -> bool:
    return any(column["name"] == name for column in columns)


def _has_index(indexes: list[dict], name: str) -> bool:
    return any(index["name"] == name for index in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "audit_events" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("audit_events")
    if not _has_column(columns, "team_id"):
        op.add_column("audit_events", sa.Column("team_id", sa.Integer(), nullable=True))
    if not _has_column(columns, "connection_id"):
        op.add_column("audit_events", sa.Column("connection_id", sa.Integer(), nullable=True))
    if not _has_column(columns, "resource_type"):
        op.add_column("audit_events", sa.Column("resource_type", sa.String(length=80), nullable=True))
    if not _has_column(columns, "resource_id"):
        op.add_column("audit_events", sa.Column("resource_id", sa.String(length=80), nullable=True))

    indexes = inspector.get_indexes("audit_events")
    if not _has_index(indexes, "ix_audit_events_team_id"):
        op.create_index("ix_audit_events_team_id", "audit_events", ["team_id"], unique=False)
    if not _has_index(indexes, "ix_audit_events_connection_id"):
        op.create_index("ix_audit_events_connection_id", "audit_events", ["connection_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "audit_events" not in inspector.get_table_names():
        return

    indexes = inspector.get_indexes("audit_events")
    if _has_index(indexes, "ix_audit_events_connection_id"):
        op.drop_index("ix_audit_events_connection_id", table_name="audit_events")
    if _has_index(indexes, "ix_audit_events_team_id"):
        op.drop_index("ix_audit_events_team_id", table_name="audit_events")

    columns = inspector.get_columns("audit_events")
    if _has_column(columns, "resource_id"):
        op.drop_column("audit_events", "resource_id")
    if _has_column(columns, "resource_type"):
        op.drop_column("audit_events", "resource_type")
    if _has_column(columns, "connection_id"):
        op.drop_column("audit_events", "connection_id")
    if _has_column(columns, "team_id"):
        op.drop_column("audit_events", "team_id")
