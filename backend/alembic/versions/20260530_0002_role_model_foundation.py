"""role model foundation

Revision ID: 20260530_0002
Revises: 20260530_0001
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0002"
down_revision = "20260530_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_created_by_user_id"), "teams", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=True)

    op.create_table(
        "platform_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_platform_audit_events_action"), "platform_audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_platform_audit_events_actor_user_id"), "platform_audit_events", ["actor_user_id"], unique=False)

    op.create_table(
        "platform_role_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_platform_role_user_role"),
    )
    op.create_index(op.f("ix_platform_role_assignments_role"), "platform_role_assignments", ["role"], unique=False)
    op.create_index(op.f("ix_platform_role_assignments_user_id"), "platform_role_assignments", ["user_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("permission", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role", "permission", name="uq_role_permission"),
    )
    op.create_index(op.f("ix_role_permissions_permission"), "role_permissions", ["permission"], unique=False)
    op.create_index(op.f("ix_role_permissions_role"), "role_permissions", ["role"], unique=False)

    op.create_table(
        "support_object_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("granted_to_user_id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=40), nullable=False),
        sa.Column("object_id", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=280), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["granted_to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_object_grants_granted_to_user_id"), "support_object_grants", ["granted_to_user_id"], unique=False)
    op.create_index(op.f("ix_support_object_grants_object_id"), "support_object_grants", ["object_id"], unique=False)
    op.create_index(op.f("ix_support_object_grants_object_type"), "support_object_grants", ["object_type"], unique=False)

    op.create_table(
        "team_invites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_invites_email"), "team_invites", ["email"], unique=False)
    op.create_index(op.f("ix_team_invites_phone"), "team_invites", ["phone"], unique=False)
    op.create_index(op.f("ix_team_invites_team_id"), "team_invites", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_invites_token_hash"), "team_invites", ["token_hash"], unique=True)

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member_team_user"),
    )
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)

    op.add_column("audit_events", sa.Column("team_id", sa.Integer(), nullable=True))
    op.add_column("audit_events", sa.Column("connection_id", sa.Integer(), nullable=True))
    op.add_column("audit_events", sa.Column("resource_type", sa.String(length=80), nullable=True))
    op.add_column("audit_events", sa.Column("resource_id", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_audit_events_team_id"), "audit_events", ["team_id"], unique=False)
    op.create_index(op.f("ix_audit_events_connection_id"), "audit_events", ["connection_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_connection_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_team_id"), table_name="audit_events")
    op.drop_column("audit_events", "resource_id")
    op.drop_column("audit_events", "resource_type")
    op.drop_column("audit_events", "connection_id")
    op.drop_column("audit_events", "team_id")

    op.drop_index(op.f("ix_team_members_user_id"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_team_id"), table_name="team_members")
    op.drop_table("team_members")

    op.drop_index(op.f("ix_team_invites_token_hash"), table_name="team_invites")
    op.drop_index(op.f("ix_team_invites_team_id"), table_name="team_invites")
    op.drop_index(op.f("ix_team_invites_phone"), table_name="team_invites")
    op.drop_index(op.f("ix_team_invites_email"), table_name="team_invites")
    op.drop_table("team_invites")

    op.drop_index(op.f("ix_support_object_grants_object_type"), table_name="support_object_grants")
    op.drop_index(op.f("ix_support_object_grants_object_id"), table_name="support_object_grants")
    op.drop_index(op.f("ix_support_object_grants_granted_to_user_id"), table_name="support_object_grants")
    op.drop_table("support_object_grants")

    op.drop_index(op.f("ix_role_permissions_role"), table_name="role_permissions")
    op.drop_index(op.f("ix_role_permissions_permission"), table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index(op.f("ix_platform_role_assignments_user_id"), table_name="platform_role_assignments")
    op.drop_index(op.f("ix_platform_role_assignments_role"), table_name="platform_role_assignments")
    op.drop_table("platform_role_assignments")

    op.drop_index(op.f("ix_platform_audit_events_actor_user_id"), table_name="platform_audit_events")
    op.drop_index(op.f("ix_platform_audit_events_action"), table_name="platform_audit_events")
    op.drop_table("platform_audit_events")

    op.drop_index(op.f("ix_teams_slug"), table_name="teams")
    op.drop_index(op.f("ix_teams_created_by_user_id"), table_name="teams")
    op.drop_table("teams")
