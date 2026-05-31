from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class UserStatus(str, Enum):
    active = "active"
    blocked = "blocked"
    deleted = "deleted"


class MessengerProvider(str, Enum):
    telegram = "telegram"
    max = "max"


class TeamRole(str, Enum):
    owner = "OWNER"
    admin = "ADMIN"
    manager = "MANAGER"
    analyst = "ANALYST"
    viewer = "VIEWER"
    agent = "AGENT"


class TeamMemberStatus(str, Enum):
    invited = "INVITED"
    active = "ACTIVE"
    suspended = "SUSPENDED"
    removed = "REMOVED"


class PlatformRole(str, Enum):
    platform_admin = "PLATFORM_ADMIN"
    support_admin = "SUPPORT_ADMIN"
    support_specialist = "SUPPORT_SPECIALIST"


class PlatformRoleStatus(str, Enum):
    active = "ACTIVE"
    suspended = "SUSPENDED"
    revoked = "REVOKED"


class Marketplace(str, Enum):
    wb = "WB"
    ozon = "OZON"
    yandex_market = "YANDEX_MARKET"


class ConnectionStatus(str, Enum):
    draft = "DRAFT"
    active = "ACTIVE"
    error = "ERROR"
    disabled = "DISABLED"


class ConnectionAccessMode(str, Enum):
    none = "NONE"
    full = "FULL"
    scoped = "SCOPED"
    read_only = "READ_ONLY"
    disabled = "DISABLED"


class ScopeSubjectType(str, Enum):
    brand = "BRAND"
    category = "CATEGORY"
    sku = "SKU"
    warehouse = "WAREHOUSE"


class SyncJobStatus(str, Enum):
    queued = "QUEUED"
    running = "RUNNING"
    success = "SUCCESS"
    failed = "FAILED"


class AiGenerationStatus(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class CredentialAuthScheme(str, Enum):
    api_key = "API_KEY"
    bearer_token = "BEARER_TOKEN"
    client_credentials = "CLIENT_CREDENTIALS"
    oauth = "OAUTH"


class SyncDomain(str, Enum):
    products = "PRODUCTS"
    prices = "PRICES"
    stocks = "STOCKS"
    orders = "ORDERS"
    returns = "RETURNS"
    finance = "FINANCE"
    ads = "ADS"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sessions: Mapped[list["SessionModel"]] = relationship(back_populates="user")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PhoneVerificationCode(Base):
    __tablename__ = "phone_verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(128), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AiGenerationLog(Base):
    __tablename__ = "ai_generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    product_row_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_products.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), default="openai", index=True)
    operation: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20), default=AiGenerationStatus.queued.value, index=True)
    model_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_vision: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_image: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    output_asset_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    request: Mapped[dict | None] = mapped_column("request_json", JSON, nullable=True)
    response: Mapped[dict | None] = mapped_column("response_json", JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_notification_channel_user_provider"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    is_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MessengerAccountLink(Base):
    __tablename__ = "messenger_account_links"
    __table_args__ = (UniqueConstraint("provider", "external_user_id", name="uq_messenger_provider_external"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    external_user_id: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member_team_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=TeamRole.viewer.value)
    status: Mapped[str] = mapped_column(String(20), default=TeamMemberStatus.active.value)
    invited_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=TeamMemberStatus.invited.value)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceConnection(Base):
    __tablename__ = "marketplace_connections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default=ConnectionStatus.draft.value, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    external_account_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_account_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column("settings_json", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ConnectionAccess(Base):
    __tablename__ = "connection_accesses"
    __table_args__ = (UniqueConstraint("connection_id", "team_member_id", name="uq_connection_access_connection_member"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    team_member_id: Mapped[int] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    access_mode: Mapped[str] = mapped_column(String(20), default=ConnectionAccessMode.full.value, index=True)
    can_read: Mapped[bool] = mapped_column(Boolean, default=True)
    can_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AccessScope(Base):
    __tablename__ = "access_scopes"
    __table_args__ = (
        UniqueConstraint("connection_access_id", "subject_type", "subject_value", name="uq_access_scope_access_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    connection_access_id: Mapped[int] = mapped_column(ForeignKey("connection_accesses.id", ondelete="CASCADE"), index=True)
    subject_type: Mapped[str] = mapped_column(String(20), index=True)
    subject_value: Mapped[str] = mapped_column(String(120), index=True)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AnalyticsProductFact(Base):
    __tablename__ = "analytics_product_facts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    warehouse: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue_amount: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SyncJobStatus.queued.value, index=True)
    domain: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    period_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceConnectionCredential(Base):
    __tablename__ = "marketplace_connection_credentials"
    __table_args__ = (
        UniqueConstraint("connection_id", "credential_kind", "name", name="uq_marketplace_credential_connection_kind_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    credential_kind: Mapped[str] = mapped_column(String(40), index=True)
    auth_scheme: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Primary")
    client_id_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_secret_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_plain: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[dict] = mapped_column("scopes_json", JSON, default=dict)
    token_meta: Mapped[dict] = mapped_column("token_meta_json", JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplaceSyncRun(Base):
    __tablename__ = "marketplace_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sync_job_id: Mapped[int | None] = mapped_column(ForeignKey("sync_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_connection_credentials.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    domain: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SyncJobStatus.queued.value, index=True)
    period_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceSyncCursor(Base):
    __tablename__ = "marketplace_sync_cursors"
    __table_args__ = (
        UniqueConstraint("connection_id", "credential_id", "provider", "domain", "cursor_key", name="uq_marketplace_sync_cursor_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_connection_credentials.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    domain: Mapped[str] = mapped_column(String(30), index=True)
    cursor_key: Mapped[str] = mapped_column(String(120), index=True)
    cursor_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplaceRawApiEvent(Base):
    __tablename__ = "marketplace_raw_api_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_connection_credentials.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    endpoint: Mapped[str] = mapped_column(String(500), index=True)
    http_method: Mapped[str] = mapped_column(String(10))
    request: Mapped[dict | None] = mapped_column("request_json", JSON, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    response: Mapped[dict | None] = mapped_column("response_json", JSON, nullable=True)
    response_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MarketplaceProduct(Base):
    __tablename__ = "marketplace_products"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "valid_from", name="uq_marketplace_product_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_offer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_sku: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    category_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    image_urls: Mapped[list] = mapped_column("image_urls_json", JSON, default=list)
    video_urls: Mapped[list] = mapped_column("video_urls_json", JSON, default=list)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplacePriceDaily(Base):
    __tablename__ = "marketplace_prices_daily"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "business_date", name="uq_marketplace_price_daily"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_offer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    business_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceStockDaily(Base):
    __tablename__ = "marketplace_stocks_daily"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_product_id", "external_offer_id", "warehouse_id", "business_date", name="uq_marketplace_stock_daily"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_offer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stock_total: Mapped[int] = mapped_column(Integer, default=0)
    stock_available: Mapped[int] = mapped_column(Integer, default=0)
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_order_id", "external_posting_id", name="uq_marketplace_order_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    external_posting_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    scheme: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplaceOrderItem(Base):
    __tablename__ = "marketplace_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("marketplace_orders.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_offer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_sku: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceReturn(Base):
    __tablename__ = "marketplace_returns"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_return_id", name="uq_marketplace_return_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_return_id: Mapped[str] = mapped_column(String(160), index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    external_posting_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplaceFinanceTransaction(Base):
    __tablename__ = "marketplace_finance_transactions"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_transaction_id", name="uq_marketplace_finance_transaction_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_transaction_id: Mapped[str] = mapped_column(String(160), index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    transaction_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    operation_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    operation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MarketplaceAdCampaign(Base):
    __tablename__ = "marketplace_ad_campaigns"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_campaign_id", name="uq_marketplace_ad_campaign_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_campaign_id: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    campaign_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    budget_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketplaceAdStatsDaily(Base):
    __tablename__ = "marketplace_ad_stats_daily"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_campaign_id", "external_product_id", "business_date", name="uq_marketplace_ad_stats_daily"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    external_campaign_id: Mapped[str] = mapped_column(String(160), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    business_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend_amount: Mapped[int] = mapped_column(Integer, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue_amount: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_event_id: Mapped[int | None] = mapped_column(ForeignKey("marketplace_raw_api_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WbTokenCapability(Base):
    __tablename__ = "wb_token_capabilities"
    __table_args__ = (
        UniqueConstraint("credential_id", "token_category", name="uq_wb_token_capability_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connection_credentials.id", ondelete="CASCADE"), index=True)
    token_category: Mapped[str] = mapped_column(String(80), index=True)
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class OzonPerformanceToken(Base):
    __tablename__ = "ozon_performance_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connection_credentials.id", ondelete="CASCADE"), index=True)
    access_token_plain: Mapped[str] = mapped_column(Text)
    token_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class YandexMarketCampaign(Base):
    __tablename__ = "yandex_market_campaigns"
    __table_args__ = (
        UniqueConstraint("connection_id", "campaign_id", name="uq_yandex_market_campaign_connection_campaign"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    business_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    campaign_id: Mapped[str] = mapped_column(String(120), index=True)
    campaign_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    placement_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    api_state: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column("payload_json", JSON, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CostImport(Base):
    __tablename__ = "cost_imports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("marketplace_connections.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(200))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DashboardRecommendation(Base):
    __tablename__ = "dashboard_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    cta_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cta_href: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    target_marketplace: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    target_team_role: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role", "permission", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    permission: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlatformRoleAssignment(Base):
    __tablename__ = "platform_role_assignments"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_platform_role_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default=PlatformRoleStatus.active.value)
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PlatformAuditEvent(Base):
    __tablename__ = "platform_audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupportObjectGrant(Base):
    __tablename__ = "support_object_grants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    granted_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    object_type: Mapped[str] = mapped_column(String(40), index=True)
    object_id: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(String(280))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
