"""sync jobs, cost imports, and dashboard recommendations

Revision ID: 20260530_0006
Revises: 20260530_0005
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0006"
down_revision = "20260530_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "sync_jobs" not in table_names:
        op.create_table(
            "sync_jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("stage", sa.String(length=40), nullable=True),
            sa.Column("dry_run", sa.Boolean(), nullable=False),
            sa.Column("processed_rows", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    sync_indexes = {index["name"] for index in inspector.get_indexes("sync_jobs")}
    if "ix_sync_jobs_team_id" not in sync_indexes:
        op.create_index(op.f("ix_sync_jobs_team_id"), "sync_jobs", ["team_id"], unique=False)
    if "ix_sync_jobs_connection_id" not in sync_indexes:
        op.create_index(op.f("ix_sync_jobs_connection_id"), "sync_jobs", ["connection_id"], unique=False)
    if "ix_sync_jobs_provider" not in sync_indexes:
        op.create_index(op.f("ix_sync_jobs_provider"), "sync_jobs", ["provider"], unique=False)
    if "ix_sync_jobs_status" not in sync_indexes:
        op.create_index(op.f("ix_sync_jobs_status"), "sync_jobs", ["status"], unique=False)
    if "ix_sync_jobs_requested_by_user_id" not in sync_indexes:
        op.create_index(op.f("ix_sync_jobs_requested_by_user_id"), "sync_jobs", ["requested_by_user_id"], unique=False)

    if "cost_imports" not in table_names:
        op.create_table(
            "cost_imports",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(length=200), nullable=False),
            sa.Column("total_rows", sa.Integer(), nullable=False),
            sa.Column("accepted_rows", sa.Integer(), nullable=False),
            sa.Column("rejected_rows", sa.Integer(), nullable=False),
            sa.Column("imported_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["imported_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    cost_indexes = {index["name"] for index in inspector.get_indexes("cost_imports")}
    if "ix_cost_imports_team_id" not in cost_indexes:
        op.create_index(op.f("ix_cost_imports_team_id"), "cost_imports", ["team_id"], unique=False)
    if "ix_cost_imports_connection_id" not in cost_indexes:
        op.create_index(op.f("ix_cost_imports_connection_id"), "cost_imports", ["connection_id"], unique=False)
    if "ix_cost_imports_imported_by_user_id" not in cost_indexes:
        op.create_index(op.f("ix_cost_imports_imported_by_user_id"), "cost_imports", ["imported_by_user_id"], unique=False)

    if "dashboard_recommendations" not in table_names:
        op.create_table(
            "dashboard_recommendations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("cta_label", sa.String(length=120), nullable=True),
            sa.Column("cta_href", sa.String(length=500), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("target_marketplace", sa.String(length=20), nullable=True),
            sa.Column("target_team_role", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    recommendation_indexes = {index["name"] for index in inspector.get_indexes("dashboard_recommendations")}
    if "ix_dashboard_recommendations_priority" not in recommendation_indexes:
        op.create_index(op.f("ix_dashboard_recommendations_priority"), "dashboard_recommendations", ["priority"], unique=False)
    if "ix_dashboard_recommendations_target_marketplace" not in recommendation_indexes:
        op.create_index(op.f("ix_dashboard_recommendations_target_marketplace"), "dashboard_recommendations", ["target_marketplace"], unique=False)
    if "ix_dashboard_recommendations_target_team_role" not in recommendation_indexes:
        op.create_index(op.f("ix_dashboard_recommendations_target_team_role"), "dashboard_recommendations", ["target_team_role"], unique=False)
    if "ix_dashboard_recommendations_is_active" not in recommendation_indexes:
        op.create_index(op.f("ix_dashboard_recommendations_is_active"), "dashboard_recommendations", ["is_active"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "dashboard_recommendations" in table_names:
        indexes = {index["name"] for index in inspector.get_indexes("dashboard_recommendations")}
        if "ix_dashboard_recommendations_is_active" in indexes:
            op.drop_index(op.f("ix_dashboard_recommendations_is_active"), table_name="dashboard_recommendations")
        if "ix_dashboard_recommendations_target_team_role" in indexes:
            op.drop_index(op.f("ix_dashboard_recommendations_target_team_role"), table_name="dashboard_recommendations")
        if "ix_dashboard_recommendations_target_marketplace" in indexes:
            op.drop_index(op.f("ix_dashboard_recommendations_target_marketplace"), table_name="dashboard_recommendations")
        if "ix_dashboard_recommendations_priority" in indexes:
            op.drop_index(op.f("ix_dashboard_recommendations_priority"), table_name="dashboard_recommendations")
        op.drop_table("dashboard_recommendations")

    if "cost_imports" in table_names:
        indexes = {index["name"] for index in inspector.get_indexes("cost_imports")}
        if "ix_cost_imports_imported_by_user_id" in indexes:
            op.drop_index(op.f("ix_cost_imports_imported_by_user_id"), table_name="cost_imports")
        if "ix_cost_imports_connection_id" in indexes:
            op.drop_index(op.f("ix_cost_imports_connection_id"), table_name="cost_imports")
        if "ix_cost_imports_team_id" in indexes:
            op.drop_index(op.f("ix_cost_imports_team_id"), table_name="cost_imports")
        op.drop_table("cost_imports")

    if "sync_jobs" in table_names:
        indexes = {index["name"] for index in inspector.get_indexes("sync_jobs")}
        if "ix_sync_jobs_requested_by_user_id" in indexes:
            op.drop_index(op.f("ix_sync_jobs_requested_by_user_id"), table_name="sync_jobs")
        if "ix_sync_jobs_status" in indexes:
            op.drop_index(op.f("ix_sync_jobs_status"), table_name="sync_jobs")
        if "ix_sync_jobs_provider" in indexes:
            op.drop_index(op.f("ix_sync_jobs_provider"), table_name="sync_jobs")
        if "ix_sync_jobs_connection_id" in indexes:
            op.drop_index(op.f("ix_sync_jobs_connection_id"), table_name="sync_jobs")
        if "ix_sync_jobs_team_id" in indexes:
            op.drop_index(op.f("ix_sync_jobs_team_id"), table_name="sync_jobs")
        op.drop_table("sync_jobs")
