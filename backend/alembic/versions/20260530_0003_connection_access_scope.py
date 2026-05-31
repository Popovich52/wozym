"""connection access and scopes

Revision ID: 20260530_0003
Revises: 20260530_0002
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0003"
down_revision = "20260530_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketplace_connections_team_id"), "marketplace_connections", ["team_id"], unique=False)
    op.create_index(op.f("ix_marketplace_connections_provider"), "marketplace_connections", ["provider"], unique=False)
    op.create_index(op.f("ix_marketplace_connections_status"), "marketplace_connections", ["status"], unique=False)
    op.create_index(op.f("ix_marketplace_connections_created_by_user_id"), "marketplace_connections", ["created_by_user_id"], unique=False)

    op.create_table(
        "connection_accesses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("team_member_id", sa.Integer(), nullable=False),
        sa.Column("access_mode", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_member_id"], ["team_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "team_member_id", name="uq_connection_access_connection_member"),
    )
    op.create_index(op.f("ix_connection_accesses_team_id"), "connection_accesses", ["team_id"], unique=False)
    op.create_index(op.f("ix_connection_accesses_connection_id"), "connection_accesses", ["connection_id"], unique=False)
    op.create_index(op.f("ix_connection_accesses_team_member_id"), "connection_accesses", ["team_member_id"], unique=False)
    op.create_index(op.f("ix_connection_accesses_access_mode"), "connection_accesses", ["access_mode"], unique=False)
    op.create_index(op.f("ix_connection_accesses_created_by_user_id"), "connection_accesses", ["created_by_user_id"], unique=False)

    op.create_table(
        "access_scopes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("connection_access_id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_value", sa.String(length=120), nullable=False),
        sa.Column("is_excluded", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_access_id"], ["connection_accesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_access_id", "subject_type", "subject_value", name="uq_access_scope_access_subject"),
    )
    op.create_index(op.f("ix_access_scopes_team_id"), "access_scopes", ["team_id"], unique=False)
    op.create_index(op.f("ix_access_scopes_connection_access_id"), "access_scopes", ["connection_access_id"], unique=False)
    op.create_index(op.f("ix_access_scopes_subject_type"), "access_scopes", ["subject_type"], unique=False)
    op.create_index(op.f("ix_access_scopes_subject_value"), "access_scopes", ["subject_value"], unique=False)
    op.create_index(op.f("ix_access_scopes_created_by_user_id"), "access_scopes", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_access_scopes_created_by_user_id"), table_name="access_scopes")
    op.drop_index(op.f("ix_access_scopes_subject_value"), table_name="access_scopes")
    op.drop_index(op.f("ix_access_scopes_subject_type"), table_name="access_scopes")
    op.drop_index(op.f("ix_access_scopes_connection_access_id"), table_name="access_scopes")
    op.drop_index(op.f("ix_access_scopes_team_id"), table_name="access_scopes")
    op.drop_table("access_scopes")

    op.drop_index(op.f("ix_connection_accesses_created_by_user_id"), table_name="connection_accesses")
    op.drop_index(op.f("ix_connection_accesses_access_mode"), table_name="connection_accesses")
    op.drop_index(op.f("ix_connection_accesses_team_member_id"), table_name="connection_accesses")
    op.drop_index(op.f("ix_connection_accesses_connection_id"), table_name="connection_accesses")
    op.drop_index(op.f("ix_connection_accesses_team_id"), table_name="connection_accesses")
    op.drop_table("connection_accesses")

    op.drop_index(op.f("ix_marketplace_connections_created_by_user_id"), table_name="marketplace_connections")
    op.drop_index(op.f("ix_marketplace_connections_status"), table_name="marketplace_connections")
    op.drop_index(op.f("ix_marketplace_connections_provider"), table_name="marketplace_connections")
    op.drop_index(op.f("ix_marketplace_connections_team_id"), table_name="marketplace_connections")
    op.drop_table("marketplace_connections")
