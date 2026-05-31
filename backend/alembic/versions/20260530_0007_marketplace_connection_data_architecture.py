"""marketplace connection credentials and data architecture

Revision ID: 20260530_0007
Revises: 20260530_0006
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0007"
down_revision = "20260530_0006"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if table_name in _table_names() and index_name in _indexes(table_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if table_name in _table_names() and column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    table_names = _table_names()

    if "marketplace_connections" in table_names:
        _add_column_if_missing("marketplace_connections", sa.Column("external_account_id", sa.String(length=120), nullable=True))
        _add_column_if_missing("marketplace_connections", sa.Column("external_account_name", sa.String(length=200), nullable=True))
        _add_column_if_missing("marketplace_connections", sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing("marketplace_connections", sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing("marketplace_connections", sa.Column("last_error_message", sa.Text(), nullable=True))
        _add_column_if_missing("marketplace_connections", sa.Column("settings_json", sa.JSON(), nullable=True))
        _create_index_if_missing("marketplace_connections", "ix_marketplace_connections_external_account_id", ["external_account_id"])

    if "connection_accesses" in table_names:
        _add_column_if_missing("connection_accesses", sa.Column("can_read", sa.Boolean(), nullable=False, server_default=sa.true()))
        _add_column_if_missing("connection_accesses", sa.Column("can_sync", sa.Boolean(), nullable=False, server_default=sa.false()))
        _add_column_if_missing("connection_accesses", sa.Column("can_manage", sa.Boolean(), nullable=False, server_default=sa.false()))
        _add_column_if_missing("connection_accesses", sa.Column("can_view_secret", sa.Boolean(), nullable=False, server_default=sa.false()))

    if "sync_jobs" in table_names:
        _add_column_if_missing("sync_jobs", sa.Column("domain", sa.String(length=30), nullable=True))
        _add_column_if_missing("sync_jobs", sa.Column("period_from", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing("sync_jobs", sa.Column("period_to", sa.DateTime(timezone=True), nullable=True))
        _create_index_if_missing("sync_jobs", "ix_sync_jobs_domain", ["domain"])

    if "marketplace_connection_credentials" not in table_names:
        op.create_table(
            "marketplace_connection_credentials",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("credential_kind", sa.String(length=40), nullable=False),
            sa.Column("auth_scheme", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("client_id_plain", sa.Text(), nullable=True),
            sa.Column("api_key_plain", sa.Text(), nullable=True),
            sa.Column("client_secret_plain", sa.Text(), nullable=True),
            sa.Column("access_token_plain", sa.Text(), nullable=True),
            sa.Column("refresh_token_plain", sa.Text(), nullable=True),
            sa.Column("scopes_json", sa.JSON(), nullable=True),
            sa.Column("token_meta_json", sa.JSON(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "credential_kind", "name", name="uq_marketplace_credential_connection_kind_name"),
        )
    for index_name, columns in {
        "ix_marketplace_connection_credentials_connection_id": ["connection_id"],
        "ix_marketplace_connection_credentials_provider": ["provider"],
        "ix_marketplace_connection_credentials_credential_kind": ["credential_kind"],
        "ix_marketplace_connection_credentials_auth_scheme": ["auth_scheme"],
        "ix_marketplace_connection_credentials_expires_at": ["expires_at"],
        "ix_marketplace_connection_credentials_is_primary": ["is_primary"],
        "ix_marketplace_connection_credentials_is_active": ["is_active"],
        "ix_marketplace_connection_credentials_created_by_user_id": ["created_by_user_id"],
    }.items():
        _create_index_if_missing("marketplace_connection_credentials", index_name, columns)

    if "marketplace_sync_runs" not in table_names:
        op.create_table(
            "marketplace_sync_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sync_job_id", sa.Integer(), nullable=True),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("credential_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("domain", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("period_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("api_calls_count", sa.Integer(), nullable=False),
            sa.Column("processed_rows", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["credential_id"], ["marketplace_connection_credentials.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    for index_name, columns in {
        "ix_marketplace_sync_runs_sync_job_id": ["sync_job_id"],
        "ix_marketplace_sync_runs_connection_id": ["connection_id"],
        "ix_marketplace_sync_runs_credential_id": ["credential_id"],
        "ix_marketplace_sync_runs_provider": ["provider"],
        "ix_marketplace_sync_runs_domain": ["domain"],
        "ix_marketplace_sync_runs_status": ["status"],
        "ix_marketplace_sync_runs_requested_by_user_id": ["requested_by_user_id"],
    }.items():
        _create_index_if_missing("marketplace_sync_runs", index_name, columns)

    if "marketplace_sync_cursors" not in table_names:
        op.create_table(
            "marketplace_sync_cursors",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("credential_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("domain", sa.String(length=30), nullable=False),
            sa.Column("cursor_key", sa.String(length=120), nullable=False),
            sa.Column("cursor_value", sa.Text(), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["credential_id"], ["marketplace_connection_credentials.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "credential_id", "provider", "domain", "cursor_key", name="uq_marketplace_sync_cursor_key"),
        )
    for index_name, columns in {
        "ix_marketplace_sync_cursors_connection_id": ["connection_id"],
        "ix_marketplace_sync_cursors_credential_id": ["credential_id"],
        "ix_marketplace_sync_cursors_provider": ["provider"],
        "ix_marketplace_sync_cursors_domain": ["domain"],
        "ix_marketplace_sync_cursors_cursor_key": ["cursor_key"],
    }.items():
        _create_index_if_missing("marketplace_sync_cursors", index_name, columns)

    if "marketplace_raw_api_events" not in table_names:
        op.create_table(
            "marketplace_raw_api_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("credential_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("endpoint", sa.String(length=500), nullable=False),
            sa.Column("http_method", sa.String(length=10), nullable=False),
            sa.Column("request_json", sa.JSON(), nullable=True),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_json", sa.JSON(), nullable=True),
            sa.Column("response_hash", sa.String(length=128), nullable=True),
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["credential_id"], ["marketplace_connection_credentials.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    for index_name, columns in {
        "ix_marketplace_raw_api_events_run_id": ["run_id"],
        "ix_marketplace_raw_api_events_connection_id": ["connection_id"],
        "ix_marketplace_raw_api_events_credential_id": ["credential_id"],
        "ix_marketplace_raw_api_events_provider": ["provider"],
        "ix_marketplace_raw_api_events_endpoint": ["endpoint"],
        "ix_marketplace_raw_api_events_response_status": ["response_status"],
        "ix_marketplace_raw_api_events_response_hash": ["response_hash"],
        "ix_marketplace_raw_api_events_fetched_at": ["fetched_at"],
    }.items():
        _create_index_if_missing("marketplace_raw_api_events", index_name, columns)

    _create_common_marketplace_tables()
    _create_provider_specific_tables()


def _create_common_marketplace_tables() -> None:
    table_names = _table_names()

    if "marketplace_products" not in table_names:
        op.create_table(
            "marketplace_products",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_product_id", sa.String(length=120), nullable=True),
            sa.Column("external_offer_id", sa.String(length=120), nullable=True),
            sa.Column("external_sku", sa.String(length=120), nullable=True),
            sa.Column("barcode", sa.String(length=120), nullable=True),
            sa.Column("name", sa.String(length=500), nullable=True),
            sa.Column("brand", sa.String(length=200), nullable=True),
            sa.Column("category_name", sa.String(length=300), nullable=True),
            sa.Column("status", sa.String(length=80), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "valid_from", name="uq_marketplace_product_version"),
        )
    for index_name, columns in {
        "ix_marketplace_products_connection_id": ["connection_id"],
        "ix_marketplace_products_provider": ["provider"],
        "ix_marketplace_products_external_product_id": ["external_product_id"],
        "ix_marketplace_products_external_offer_id": ["external_offer_id"],
        "ix_marketplace_products_external_sku": ["external_sku"],
        "ix_marketplace_products_barcode": ["barcode"],
        "ix_marketplace_products_brand": ["brand"],
        "ix_marketplace_products_category_name": ["category_name"],
        "ix_marketplace_products_status": ["status"],
        "ix_marketplace_products_source_run_id": ["source_run_id"],
        "ix_marketplace_products_raw_event_id": ["raw_event_id"],
        "ix_marketplace_products_valid_from": ["valid_from"],
        "ix_marketplace_products_valid_to": ["valid_to"],
        "ix_marketplace_products_is_current": ["is_current"],
    }.items():
        _create_index_if_missing("marketplace_products", index_name, columns)

    if "marketplace_prices_daily" not in table_names:
        op.create_table(
            "marketplace_prices_daily",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_product_id", sa.String(length=120), nullable=True),
            sa.Column("external_offer_id", sa.String(length=120), nullable=True),
            sa.Column("business_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("price_amount", sa.Integer(), nullable=True),
            sa.Column("old_price_amount", sa.Integer(), nullable=True),
            sa.Column("discount_price_amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "business_date", name="uq_marketplace_price_daily"),
        )
    for index_name, columns in {
        "ix_marketplace_prices_daily_connection_id": ["connection_id"],
        "ix_marketplace_prices_daily_provider": ["provider"],
        "ix_marketplace_prices_daily_external_product_id": ["external_product_id"],
        "ix_marketplace_prices_daily_external_offer_id": ["external_offer_id"],
        "ix_marketplace_prices_daily_business_date": ["business_date"],
        "ix_marketplace_prices_daily_source_run_id": ["source_run_id"],
        "ix_marketplace_prices_daily_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_prices_daily", index_name, columns)

    if "marketplace_stocks_daily" not in table_names:
        op.create_table(
            "marketplace_stocks_daily",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_product_id", sa.String(length=120), nullable=True),
            sa.Column("external_offer_id", sa.String(length=120), nullable=True),
            sa.Column("warehouse_id", sa.String(length=120), nullable=True),
            sa.Column("warehouse_name", sa.String(length=200), nullable=True),
            sa.Column("business_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("stock_total", sa.Integer(), nullable=False),
            sa.Column("stock_available", sa.Integer(), nullable=False),
            sa.Column("stock_reserved", sa.Integer(), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "warehouse_id", "business_date", name="uq_marketplace_stock_daily"),
        )
    for index_name, columns in {
        "ix_marketplace_stocks_daily_connection_id": ["connection_id"],
        "ix_marketplace_stocks_daily_provider": ["provider"],
        "ix_marketplace_stocks_daily_external_product_id": ["external_product_id"],
        "ix_marketplace_stocks_daily_external_offer_id": ["external_offer_id"],
        "ix_marketplace_stocks_daily_warehouse_id": ["warehouse_id"],
        "ix_marketplace_stocks_daily_business_date": ["business_date"],
        "ix_marketplace_stocks_daily_source_run_id": ["source_run_id"],
        "ix_marketplace_stocks_daily_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_stocks_daily", index_name, columns)

    _create_order_return_finance_ad_tables()


def _create_order_return_finance_ad_tables() -> None:
    table_names = _table_names()

    if "marketplace_orders" not in table_names:
        op.create_table(
            "marketplace_orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_order_id", sa.String(length=160), nullable=True),
            sa.Column("external_posting_id", sa.String(length=160), nullable=True),
            sa.Column("status", sa.String(length=80), nullable=True),
            sa.Column("scheme", sa.String(length=40), nullable=True),
            sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("total_amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_order_id", "external_posting_id", name="uq_marketplace_order_external"),
        )
    for index_name, columns in {
        "ix_marketplace_orders_connection_id": ["connection_id"],
        "ix_marketplace_orders_provider": ["provider"],
        "ix_marketplace_orders_external_order_id": ["external_order_id"],
        "ix_marketplace_orders_external_posting_id": ["external_posting_id"],
        "ix_marketplace_orders_status": ["status"],
        "ix_marketplace_orders_scheme": ["scheme"],
        "ix_marketplace_orders_ordered_at": ["ordered_at"],
        "ix_marketplace_orders_source_run_id": ["source_run_id"],
        "ix_marketplace_orders_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_orders", index_name, columns)

    if "marketplace_order_items" not in table_names:
        op.create_table(
            "marketplace_order_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_product_id", sa.String(length=120), nullable=True),
            sa.Column("external_offer_id", sa.String(length=120), nullable=True),
            sa.Column("external_sku", sa.String(length=120), nullable=True),
            sa.Column("name", sa.String(length=500), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("price_amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["marketplace_orders.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    for index_name, columns in {
        "ix_marketplace_order_items_order_id": ["order_id"],
        "ix_marketplace_order_items_connection_id": ["connection_id"],
        "ix_marketplace_order_items_provider": ["provider"],
        "ix_marketplace_order_items_external_product_id": ["external_product_id"],
        "ix_marketplace_order_items_external_offer_id": ["external_offer_id"],
        "ix_marketplace_order_items_external_sku": ["external_sku"],
    }.items():
        _create_index_if_missing("marketplace_order_items", index_name, columns)

    if "marketplace_returns" not in table_names:
        op.create_table(
            "marketplace_returns",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_return_id", sa.String(length=160), nullable=False),
            sa.Column("external_order_id", sa.String(length=160), nullable=True),
            sa.Column("external_posting_id", sa.String(length=160), nullable=True),
            sa.Column("status", sa.String(length=80), nullable=True),
            sa.Column("reason", sa.String(length=300), nullable=True),
            sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_return_id", name="uq_marketplace_return_external"),
        )
    for index_name, columns in {
        "ix_marketplace_returns_connection_id": ["connection_id"],
        "ix_marketplace_returns_provider": ["provider"],
        "ix_marketplace_returns_external_return_id": ["external_return_id"],
        "ix_marketplace_returns_external_order_id": ["external_order_id"],
        "ix_marketplace_returns_external_posting_id": ["external_posting_id"],
        "ix_marketplace_returns_status": ["status"],
        "ix_marketplace_returns_returned_at": ["returned_at"],
        "ix_marketplace_returns_source_run_id": ["source_run_id"],
        "ix_marketplace_returns_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_returns", index_name, columns)

    if "marketplace_finance_transactions" not in table_names:
        op.create_table(
            "marketplace_finance_transactions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_transaction_id", sa.String(length=160), nullable=False),
            sa.Column("external_order_id", sa.String(length=160), nullable=True),
            sa.Column("transaction_type", sa.String(length=120), nullable=True),
            sa.Column("operation_type", sa.String(length=120), nullable=True),
            sa.Column("operation_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_transaction_id", name="uq_marketplace_finance_transaction_external"),
        )
    for index_name, columns in {
        "ix_marketplace_finance_transactions_connection_id": ["connection_id"],
        "ix_marketplace_finance_transactions_provider": ["provider"],
        "ix_marketplace_finance_transactions_external_transaction_id": ["external_transaction_id"],
        "ix_marketplace_finance_transactions_external_order_id": ["external_order_id"],
        "ix_marketplace_finance_transactions_transaction_type": ["transaction_type"],
        "ix_marketplace_finance_transactions_operation_type": ["operation_type"],
        "ix_marketplace_finance_transactions_operation_at": ["operation_at"],
        "ix_marketplace_finance_transactions_source_run_id": ["source_run_id"],
        "ix_marketplace_finance_transactions_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_finance_transactions", index_name, columns)

    _create_ad_tables()


def _create_ad_tables() -> None:
    table_names = _table_names()

    if "marketplace_ad_campaigns" not in table_names:
        op.create_table(
            "marketplace_ad_campaigns",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_campaign_id", sa.String(length=160), nullable=False),
            sa.Column("name", sa.String(length=300), nullable=True),
            sa.Column("campaign_type", sa.String(length=80), nullable=True),
            sa.Column("status", sa.String(length=80), nullable=True),
            sa.Column("budget_amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_campaign_id", name="uq_marketplace_ad_campaign_external"),
        )
    for index_name, columns in {
        "ix_marketplace_ad_campaigns_connection_id": ["connection_id"],
        "ix_marketplace_ad_campaigns_provider": ["provider"],
        "ix_marketplace_ad_campaigns_external_campaign_id": ["external_campaign_id"],
        "ix_marketplace_ad_campaigns_campaign_type": ["campaign_type"],
        "ix_marketplace_ad_campaigns_status": ["status"],
        "ix_marketplace_ad_campaigns_source_run_id": ["source_run_id"],
        "ix_marketplace_ad_campaigns_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_ad_campaigns", index_name, columns)

    if "marketplace_ad_stats_daily" not in table_names:
        op.create_table(
            "marketplace_ad_stats_daily",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("external_campaign_id", sa.String(length=160), nullable=False),
            sa.Column("external_product_id", sa.String(length=120), nullable=True),
            sa.Column("business_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("impressions", sa.Integer(), nullable=False),
            sa.Column("clicks", sa.Integer(), nullable=False),
            sa.Column("spend_amount", sa.Integer(), nullable=False),
            sa.Column("orders_count", sa.Integer(), nullable=False),
            sa.Column("revenue_amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("source_run_id", sa.Integer(), nullable=True),
            sa.Column("raw_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["raw_event_id"], ["marketplace_raw_api_events.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_run_id"], ["marketplace_sync_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "external_campaign_id", "external_product_id", "business_date", name="uq_marketplace_ad_stats_daily"),
        )
    for index_name, columns in {
        "ix_marketplace_ad_stats_daily_connection_id": ["connection_id"],
        "ix_marketplace_ad_stats_daily_provider": ["provider"],
        "ix_marketplace_ad_stats_daily_external_campaign_id": ["external_campaign_id"],
        "ix_marketplace_ad_stats_daily_external_product_id": ["external_product_id"],
        "ix_marketplace_ad_stats_daily_business_date": ["business_date"],
        "ix_marketplace_ad_stats_daily_source_run_id": ["source_run_id"],
        "ix_marketplace_ad_stats_daily_raw_event_id": ["raw_event_id"],
    }.items():
        _create_index_if_missing("marketplace_ad_stats_daily", index_name, columns)


def _create_provider_specific_tables() -> None:
    table_names = _table_names()

    if "wb_token_capabilities" not in table_names:
        op.create_table(
            "wb_token_capabilities",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("credential_id", sa.Integer(), nullable=False),
            sa.Column("token_category", sa.String(length=80), nullable=False),
            sa.Column("is_read_only", sa.Boolean(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["credential_id"], ["marketplace_connection_credentials.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("credential_id", "token_category", name="uq_wb_token_capability_category"),
        )
    for index_name, columns in {
        "ix_wb_token_capabilities_credential_id": ["credential_id"],
        "ix_wb_token_capabilities_token_category": ["token_category"],
        "ix_wb_token_capabilities_expires_at": ["expires_at"],
        "ix_wb_token_capabilities_checked_at": ["checked_at"],
    }.items():
        _create_index_if_missing("wb_token_capabilities", index_name, columns)

    if "ozon_performance_tokens" not in table_names:
        op.create_table(
            "ozon_performance_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("credential_id", sa.Integer(), nullable=False),
            sa.Column("access_token_plain", sa.Text(), nullable=False),
            sa.Column("token_type", sa.String(length=40), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["credential_id"], ["marketplace_connection_credentials.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    for index_name, columns in {
        "ix_ozon_performance_tokens_credential_id": ["credential_id"],
        "ix_ozon_performance_tokens_expires_at": ["expires_at"],
        "ix_ozon_performance_tokens_fetched_at": ["fetched_at"],
    }.items():
        _create_index_if_missing("ozon_performance_tokens", index_name, columns)

    if "yandex_market_campaigns" not in table_names:
        op.create_table(
            "yandex_market_campaigns",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("connection_id", sa.Integer(), nullable=False),
            sa.Column("business_id", sa.String(length=120), nullable=True),
            sa.Column("campaign_id", sa.String(length=120), nullable=False),
            sa.Column("campaign_name", sa.String(length=300), nullable=True),
            sa.Column("placement_type", sa.String(length=80), nullable=True),
            sa.Column("api_state", sa.String(length=80), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["marketplace_connections.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "campaign_id", name="uq_yandex_market_campaign_connection_campaign"),
        )
    for index_name, columns in {
        "ix_yandex_market_campaigns_connection_id": ["connection_id"],
        "ix_yandex_market_campaigns_business_id": ["business_id"],
        "ix_yandex_market_campaigns_campaign_id": ["campaign_id"],
        "ix_yandex_market_campaigns_placement_type": ["placement_type"],
        "ix_yandex_market_campaigns_api_state": ["api_state"],
        "ix_yandex_market_campaigns_last_seen_at": ["last_seen_at"],
    }.items():
        _create_index_if_missing("yandex_market_campaigns", index_name, columns)


def downgrade() -> None:
    for table_name in [
        "yandex_market_campaigns",
        "ozon_performance_tokens",
        "wb_token_capabilities",
        "marketplace_ad_stats_daily",
        "marketplace_ad_campaigns",
        "marketplace_finance_transactions",
        "marketplace_returns",
        "marketplace_order_items",
        "marketplace_orders",
        "marketplace_stocks_daily",
        "marketplace_prices_daily",
        "marketplace_products",
        "marketplace_raw_api_events",
        "marketplace_sync_cursors",
        "marketplace_sync_runs",
        "marketplace_connection_credentials",
    ]:
        if table_name in _table_names():
            op.drop_table(table_name)

    if "sync_jobs" in _table_names():
        _drop_index_if_exists("sync_jobs", "ix_sync_jobs_domain")
        _drop_column_if_exists("sync_jobs", "period_to")
        _drop_column_if_exists("sync_jobs", "period_from")
        _drop_column_if_exists("sync_jobs", "domain")

    if "connection_accesses" in _table_names():
        _drop_column_if_exists("connection_accesses", "can_view_secret")
        _drop_column_if_exists("connection_accesses", "can_manage")
        _drop_column_if_exists("connection_accesses", "can_sync")
        _drop_column_if_exists("connection_accesses", "can_read")

    if "marketplace_connections" in _table_names():
        _drop_index_if_exists("marketplace_connections", "ix_marketplace_connections_external_account_id")
        _drop_column_if_exists("marketplace_connections", "settings_json")
        _drop_column_if_exists("marketplace_connections", "last_error_message")
        _drop_column_if_exists("marketplace_connections", "last_error_at")
        _drop_column_if_exists("marketplace_connections", "last_success_at")
        _drop_column_if_exists("marketplace_connections", "external_account_name")
        _drop_column_if_exists("marketplace_connections", "external_account_id")
