from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ErrorResponse(BaseModel):
    error: dict


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    password: str = Field(min_length=8)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    login: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyPhoneRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    email: str
    phone: str
    name: str | None
    email_verified_at: datetime | None
    phone_verified_at: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthTokensOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageOut(BaseModel):
    message: str


class MeUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SessionOut(BaseModel):
    id: int
    user_agent: str | None
    ip_address: str | None
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=64)


class TeamPatchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class TeamOut(BaseModel):
    id: int
    slug: str
    name: str
    is_active: bool
    created_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberOut(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformActorOut(BaseModel):
    id: int
    user_id: int
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamInviteCreateRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    role: str = Field(default="VIEWER")


class TeamInviteOut(BaseModel):
    id: int
    team_id: int
    email: str | None
    phone: str | None
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberPatchRequest(BaseModel):
    role: str | None = Field(default=None)
    status: str | None = Field(default=None)


class MarketplaceConnectionCreateRequest(BaseModel):
    provider: str
    name: str = Field(min_length=2, max_length=120)


class MarketplaceConnectionPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    status: str | None = Field(default=None)
    is_disabled: bool | None = Field(default=None)


class MarketplaceConnectionOut(BaseModel):
    id: int
    team_id: int
    provider: str
    name: str
    status: str
    is_disabled: bool
    external_account_id: str | None
    external_account_name: str | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None
    created_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceCredentialCreateRequest(BaseModel):
    credential_kind: str = Field(min_length=2, max_length=40)
    auth_scheme: str = Field(min_length=2, max_length=32)
    name: str = Field(default="Primary", min_length=1, max_length=120)
    client_id_plain: str | None = None
    api_key_plain: str | None = None
    client_secret_plain: str | None = None
    access_token_plain: str | None = None
    refresh_token_plain: str | None = None
    scopes_json: dict = Field(default_factory=dict)
    token_meta_json: dict = Field(default_factory=dict)
    expires_at: datetime | None = None
    is_primary: bool = True
    is_active: bool = True


class MarketplaceCredentialPatchRequest(BaseModel):
    credential_kind: str | None = Field(default=None, min_length=2, max_length=40)
    auth_scheme: str | None = Field(default=None, min_length=2, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    client_id_plain: str | None = None
    api_key_plain: str | None = None
    client_secret_plain: str | None = None
    access_token_plain: str | None = None
    refresh_token_plain: str | None = None
    scopes_json: dict | None = None
    token_meta_json: dict | None = None
    expires_at: datetime | None = None
    is_primary: bool | None = None
    is_active: bool | None = None


class MarketplaceCredentialOut(BaseModel):
    id: int
    connection_id: int
    provider: str
    credential_kind: str
    auth_scheme: str
    name: str
    client_id_plain: str | None
    api_key_plain: str | None
    client_secret_plain: str | None
    access_token_plain: str | None
    refresh_token_plain: str | None
    scopes: dict
    token_meta: dict
    expires_at: datetime | None
    last_checked_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    is_primary: bool
    is_active: bool
    created_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OzonSellerKeyValidationRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=120)
    api_key: str = Field(min_length=1, max_length=512)


class OzonPerformanceKeyValidationRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)
    client_secret: str = Field(min_length=1, max_length=2048)


class MarketplaceKeyValidationOut(BaseModel):
    is_valid: bool
    status_code: int | None
    message: str
    checked_at: datetime
    details: dict = Field(default_factory=dict)


class ConnectionAccessCreateRequest(BaseModel):
    team_member_id: int
    access_mode: str = Field(default="FULL")
    is_active: bool = True


class ConnectionAccessPatchRequest(BaseModel):
    access_mode: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class AccessScopeCreateRequest(BaseModel):
    subject_type: str
    subject_value: str = Field(min_length=1, max_length=120)
    is_excluded: bool = False


class AccessScopePatchRequest(BaseModel):
    subject_type: str | None = Field(default=None)
    subject_value: str | None = Field(default=None, min_length=1, max_length=120)
    is_excluded: bool | None = Field(default=None)


class AccessScopeOut(BaseModel):
    id: int
    team_id: int
    connection_access_id: int
    subject_type: str
    subject_value: str
    is_excluded: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionAccessOut(BaseModel):
    id: int
    team_id: int
    connection_id: int
    team_member_id: int
    access_mode: str
    can_read: bool
    can_sync: bool
    can_manage: bool
    can_view_secret: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsProductOut(BaseModel):
    id: int
    team_id: int
    connection_id: int
    sku: str
    brand: str
    category: str
    warehouse: str | None
    orders_count: int
    revenue_amount: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceProductOut(BaseModel):
    id: int
    connection_id: int
    provider: str
    external_product_id: str | None
    external_offer_id: str | None
    external_sku: str | None
    barcode: str | None
    name: str | None
    brand: str | None
    category_name: str | None
    status: str | None
    payload: dict = Field(default_factory=dict)
    image_urls: list[str]
    video_urls: list[str]
    is_current: bool
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OzonProductMediaSaveRequest(BaseModel):
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    video_cover_url: str | None = None


class OzonProductMediaSaveOut(BaseModel):
    saved_images: int = 0
    saved_videos: int = 0
    cover_applied: bool = False
    task_ids: list[int] = Field(default_factory=list)
    message: str


class OzonProductCreateRequest(BaseModel):
    offer_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    description_category_id: int = Field(ge=1)
    type_id: int = Field(ge=1)
    barcode: str | None = Field(default=None, max_length=120)
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    video_cover_url: str | None = None
    attributes: list[dict] = Field(default_factory=list)
    complex_attributes: list[dict] = Field(default_factory=list)
    dimension_unit: str = Field(default="mm", max_length=10)
    depth: int = Field(default=100, ge=0)
    width: int = Field(default=100, ge=0)
    height: int = Field(default=100, ge=0)
    weight_unit: str = Field(default="g", max_length=10)
    weight: int = Field(default=100, ge=0)
    price: str | None = None
    old_price: str | None = None
    currency_code: str = Field(default="RUB", max_length=8)


class OzonProductCreateOut(BaseModel):
    offer_id: str
    task_id: int | None
    import_status: str | None
    product_id: int | None
    message: str
    errors: list[dict] = Field(default_factory=list)


class OzonAttributeOut(BaseModel):
    id: int
    attribute_complex_id: int
    name: str
    description: str | None
    type: str | None
    is_collection: bool
    is_required: bool
    max_value_count: int | None
    dictionary_id: int | None
    group_name: str | None


class OzonAttributeValueOut(BaseModel):
    id: int
    value: str
    info: str | None = None
    picture: str | None = None


class OzonContentRatingRefreshRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=1000)
    product_row_ids: list[int] = Field(default_factory=list)
    only_missing: bool = False


class OzonContentRatingConditionOut(BaseModel):
    key: str | None = None
    description: str | None = None
    fulfilled: bool = False
    cost: float | None = None


class OzonContentRatingImproveAttributeOut(BaseModel):
    id: int | None = None
    name: str | None = None


class OzonContentRatingGroupOut(BaseModel):
    key: str | None = None
    name: str | None = None
    rating: float | None = None
    weight: float | None = None
    improve_at_least: int | None = None
    missing_conditions: list[OzonContentRatingConditionOut] = Field(default_factory=list)
    improve_attributes: list[OzonContentRatingImproveAttributeOut] = Field(default_factory=list)


class OzonContentRatingItemOut(BaseModel):
    product_row_id: int
    sku: str
    offer_id: str | None = None
    rating: float | None = None
    groups: list[OzonContentRatingGroupOut] = Field(default_factory=list)
    fetched_at: datetime


class OzonContentRatingRefreshOut(BaseModel):
    updated_count: int
    requested_skus: int
    items: list[OzonContentRatingItemOut] = Field(default_factory=list)
    message: str


class AiCardDraftRequest(BaseModel):
    current_fields: dict = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    template_id: str | None = Field(default=None, max_length=120)
    user_prompt: str | None = Field(default=None, max_length=4000)
    reference: dict = Field(default_factory=dict)
    goals: dict = Field(default_factory=dict)


class AiCardDraftOut(BaseModel):
    draft_id: int
    log_id: int
    status: str
    model: str
    photo_analysis: dict = Field(default_factory=dict)
    field_checks: list[dict] = Field(default_factory=list)
    field_recommendations: list[dict] = Field(default_factory=list)
    media_recommendations: list[dict] = Field(default_factory=list)
    draft: dict = Field(default_factory=dict)
    prompt_analysis: dict = Field(default_factory=dict)
    reference_analysis: dict = Field(default_factory=dict)
    template_plan: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)


class AiMediaGenerateRequest(BaseModel):
    source_image_url: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=4000)
    reference: dict = Field(default_factory=dict)
    output_format: str = Field(default="png", max_length=10)
    size: str = Field(default="1024x1024", max_length=20)


class AiMediaGenerateOut(BaseModel):
    log_id: int
    status: str
    model: str
    image_url: str | None = None
    revised_prompt: str | None = None
    progress: int = 0
    message: str | None = None
    error_message: str | None = None
    usage: dict = Field(default_factory=dict)


class AgentChatRequest(BaseModel):
    team_id: int = Field(ge=1)
    connection_id: int | None = Field(default=None, ge=1)
    message: str = Field(min_length=1, max_length=4000)
    execute_tool: bool = False
    write_mode: bool = False


class AgentChatOut(BaseModel):
    message: str
    context: dict


class SyncRunRequest(BaseModel):
    dry_run: bool = False
    stage: str | None = Field(default=None, max_length=40)


class SyncJobOut(BaseModel):
    id: int
    team_id: int
    connection_id: int
    provider: str
    status: str
    domain: str | None
    period_from: datetime | None
    period_to: datetime | None
    stage: str | None
    dry_run: bool
    processed_rows: int
    error_message: str | None
    requested_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CostImportRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=200)
    total_rows: int = Field(ge=0)
    accepted_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)


class CostImportOut(BaseModel):
    id: int
    team_id: int
    connection_id: int
    file_name: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    imported_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardRecommendationCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=5, max_length=5000)
    cta_label: str | None = Field(default=None, max_length=120)
    cta_href: str | None = Field(default=None, max_length=500)
    priority: int = Field(default=100, ge=0, le=10000)
    target_marketplace: str | None = Field(default=None, max_length=20)
    target_team_role: str | None = Field(default=None, max_length=20)
    is_active: bool = True


class DashboardRecommendationPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, min_length=5, max_length=5000)
    cta_label: str | None = Field(default=None, max_length=120)
    cta_href: str | None = Field(default=None, max_length=500)
    priority: int | None = Field(default=None, ge=0, le=10000)
    target_marketplace: str | None = Field(default=None, max_length=20)
    target_team_role: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class DashboardRecommendationOut(BaseModel):
    id: int
    title: str
    body: str
    cta_label: str | None
    cta_href: str | None
    priority: int
    target_marketplace: str | None
    target_team_role: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    team_id: int
    connection_id: int | None
    products_total: int
    orders_total: int
    revenue_total: int
    recommendations: list[DashboardRecommendationOut]


class AuditEventOut(BaseModel):
    id: int
    user_id: int | None
    team_id: int | None
    connection_id: int | None
    resource_type: str | None
    resource_id: str | None
    action: str
    meta: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AiGenerationLogOut(BaseModel):
    id: int
    team_id: int | None
    connection_id: int | None
    product_row_id: int | None
    user_id: int | None
    provider: str
    operation: str
    status: str
    model_text: str | None
    model_vision: str | None
    model_image: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    image_count: int
    output_asset_count: int
    estimated_cost_microusd: int | None
    latency_ms: int | None
    trace_id: str | None
    request: dict | None
    response: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
