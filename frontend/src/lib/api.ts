"use client";

export type ApiError = {
  detail?: string;
  error?: { code?: string; message?: string };
};

export type User = {
  id: number;
  email: string;
  phone: string;
  name: string | null;
  email_verified_at: string | null;
  phone_verified_at: string | null;
  status: string;
  created_at: string;
};

export type SessionItem = {
  id: number;
  user_agent: string | null;
  ip_address: string | null;
  expires_at: string;
  created_at: string;
};

export type Team = {
  id: number;
  slug: string;
  name: string;
  is_active: boolean;
  created_by_user_id: number;
  created_at: string;
};

export type TeamMember = {
  id: number;
  team_id: number;
  user_id: number;
  role: string;
  status: string;
  created_at: string;
};

export type TeamInvite = {
  id: number;
  team_id: number;
  email: string | null;
  phone: string | null;
  role: string;
  status: string;
  expires_at: string;
  created_at: string;
};

export type MarketplaceConnection = {
  id: number;
  team_id: number;
  provider: string;
  name: string;
  status: string;
  is_disabled: boolean;
  external_account_id: string | null;
  external_account_name: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  created_by_user_id: number;
  created_at: string;
};

export type MarketplaceCredential = {
  id: number;
  connection_id: number;
  provider: string;
  credential_kind: string;
  auth_scheme: string;
  name: string;
  client_id_plain: string | null;
  api_key_plain: string | null;
  client_secret_plain: string | null;
  access_token_plain: string | null;
  refresh_token_plain: string | null;
  scopes: Record<string, unknown>;
  token_meta: Record<string, unknown>;
  expires_at: string | null;
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_by_user_id: number;
  created_at: string;
};

export type MarketplaceCredentialPayload = {
  credential_kind?: string;
  auth_scheme?: string;
  name?: string;
  client_id_plain?: string | null;
  api_key_plain?: string | null;
  client_secret_plain?: string | null;
  access_token_plain?: string | null;
  refresh_token_plain?: string | null;
  scopes_json?: Record<string, unknown>;
  token_meta_json?: Record<string, unknown>;
  expires_at?: string | null;
  is_primary?: boolean;
  is_active?: boolean;
};

export type MarketplaceKeyValidation = {
  is_valid: boolean;
  status_code: number | null;
  message: string;
  checked_at: string;
  details: Record<string, unknown>;
};

export type ConnectionAccess = {
  id: number;
  team_id: number;
  connection_id: number;
  team_member_id: number;
  access_mode: string;
  can_read: boolean;
  can_sync: boolean;
  can_manage: boolean;
  can_view_secret: boolean;
  is_active: boolean;
  created_at: string;
};

export type AccessScope = {
  id: number;
  team_id: number;
  connection_access_id: number;
  subject_type: string;
  subject_value: string;
  is_excluded: boolean;
  created_at: string;
};

export type TeamAudit = {
  id: number;
  user_id: number | null;
  team_id: number | null;
  connection_id: number | null;
  resource_type: string | null;
  resource_id: string | null;
  action: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type PlatformActor = {
  id: number;
  user_id: number;
  role: string;
  status: string;
  created_at: string;
};

export type PlatformStats = {
  teams_total: number;
  users_total: number;
};

export type PlatformUser = {
  id: number;
  email: string;
  phone: string;
  telegram: string | null;
  max: string | null;
  status: string;
  registered_at: string;
};

export type PlatformTeam = {
  id: number;
  slug: string;
  name: string;
  is_active: boolean;
  created_at: string;
};

export type DashboardRecommendation = {
  id: number;
  title: string;
  body: string;
  cta_label: string | null;
  cta_href: string | null;
  priority: number;
  target_marketplace: string | null;
  target_team_role: string | null;
  is_active: boolean;
  created_at: string;
};

export type TeamDashboard = {
  team_id: number;
  connection_id: number | null;
  products_total: number;
  orders_total: number;
  revenue_total: number;
  recommendations: DashboardRecommendation[];
};

export type AnalyticsProduct = {
  id: number;
  team_id: number;
  connection_id: number;
  sku: string;
  brand: string;
  category: string;
  warehouse: string | null;
  orders_count: number;
  revenue_amount: number;
  created_at: string;
};

export type MarketplaceProductItem = {
  id: number;
  connection_id: number;
  provider: string;
  external_product_id: string | null;
  external_offer_id: string | null;
  external_sku: string | null;
  barcode: string | null;
  name: string | null;
  brand: string | null;
  category_name: string | null;
  status: string | null;
  payload: Record<string, unknown>;
  image_urls: string[];
  video_urls: string[];
  is_current: boolean;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
};

export type OzonProductMediaSaveResult = {
  saved_images: number;
  saved_videos: number;
  cover_applied: boolean;
  task_ids: number[];
  message: string;
};

export type OzonProductCreateResult = {
  offer_id: string;
  task_id: number | null;
  import_status: string | null;
  product_id: number | null;
  message: string;
  errors: Array<Record<string, unknown>>;
};

export type OzonAttribute = {
  id: number;
  attribute_complex_id: number;
  name: string;
  description: string | null;
  type: string | null;
  is_collection: boolean;
  is_required: boolean;
  max_value_count: number | null;
  dictionary_id: number | null;
  group_name: string | null;
};

export type OzonAttributeValue = {
  id: number;
  value: string;
  info: string | null;
  picture: string | null;
};

export type OzonContentRatingCondition = {
  key: string | null;
  description: string | null;
  fulfilled: boolean;
  cost: number | null;
};

export type OzonContentRatingImproveAttribute = {
  id: number | null;
  name: string | null;
};

export type OzonContentRatingGroup = {
  key: string | null;
  name: string | null;
  rating: number | null;
  weight: number | null;
  improve_at_least: number | null;
  missing_conditions: OzonContentRatingCondition[];
  improve_attributes: OzonContentRatingImproveAttribute[];
};

export type OzonContentRatingItem = {
  product_row_id: number;
  sku: string;
  offer_id: string | null;
  rating: number | null;
  groups: OzonContentRatingGroup[];
  fetched_at: string;
};

export type OzonContentRatingRefreshResult = {
  updated_count: number;
  requested_skus: number;
  items: OzonContentRatingItem[];
  message: string;
};

export type SyncJob = {
  id: number;
  team_id: number;
  connection_id: number;
  provider: string;
  status: string;
  domain: string | null;
  period_from: string | null;
  period_to: string | null;
  stage: string | null;
  dry_run: boolean;
  processed_rows: number;
  error_message: string | null;
  requested_by_user_id: number;
  created_at: string;
};

export type CostImport = {
  id: number;
  team_id: number;
  connection_id: number;
  file_name: string;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  imported_by_user_id: number;
  created_at: string;
};

export type AgentChatResult = {
  message: string;
  context: Record<string, unknown>;
};

export type AiGenerationLog = {
  id: number;
  team_id: number | null;
  connection_id: number | null;
  product_row_id: number | null;
  user_id: number | null;
  provider: string;
  operation: string;
  status: string;
  model_text: string | null;
  model_vision: string | null;
  model_image: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_input_tokens: number;
  reasoning_tokens: number;
  image_count: number;
  output_asset_count: number;
  estimated_cost_microusd: number | null;
  latency_ms: number | null;
  trace_id: string | null;
  request: Record<string, unknown> | null;
  response: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type AiCardDraftResult = {
  draft_id: number;
  log_id: number;
  status: string;
  model: string;
  photo_analysis: Record<string, unknown>;
  field_checks: Array<Record<string, unknown>>;
  field_recommendations: Array<Record<string, unknown>>;
  media_recommendations: Array<Record<string, unknown>>;
  draft: Record<string, unknown>;
  prompt_analysis: Record<string, unknown>;
  reference_analysis: Record<string, unknown>;
  template_plan: Record<string, unknown>;
  warnings: string[];
  usage: Record<string, unknown>;
};

export type AiMediaGenerateResult = {
  log_id: number;
  status: string;
  model: string;
  image_url: string | null;
  revised_prompt: string | null;
  progress: number;
  message: string | null;
  error_message: string | null;
  usage: Record<string, unknown>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/backend";
const TOKEN_KEY = "wozym_access_token";

async function refreshAccessToken(): Promise<string | null> {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) return null;
  const payload = (await response.json()) as { access_token?: string };
  if (!payload.access_token) return null;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, payload.access_token);
  }
  return payload.access_token;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string, options: { timeoutMs?: number } = {}): Promise<T> {
  const controller = options.timeoutMs ? new AbortController() : undefined;
  const timeoutId = controller && options.timeoutMs ? window.setTimeout(() => controller.abort(), options.timeoutMs) : null;
  const buildRequest = (activeToken?: string): RequestInit => ({
    ...init,
    signal: controller?.signal ?? init.signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
      ...(init.headers || {}),
    },
  });

  try {
    let response = await fetch(`${API_URL}${path}`, buildRequest(token));
    if (response.status === 401 && token) {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        response = await fetch(`${API_URL}${path}`, buildRequest(refreshedToken));
      }
    }

    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as ApiError;
      const message = payload.detail || payload.error?.message || "Request failed";
      throw new Error(message);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. Проверьте AI logs: запрос мог завершиться на сервере позже.");
    }
    throw err;
  } finally {
    if (timeoutId !== null) window.clearTimeout(timeoutId);
  }
}

export async function register(input: { name?: string; email: string; phone: string; password: string }) {
  return request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function login(input: { login: string; password: string }) {
  return request<{ access_token: string; token_type: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function logout(token: string) {
  return request<{ message: string }>("/auth/logout", { method: "POST" }, token);
}

export async function verifyEmail(tokenValue: string) {
  return request<{ message: string }>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token: tokenValue }),
  });
}

export async function verifyPhone(code: string, token: string) {
  return request<{ message: string }>(
    "/auth/verify-phone",
    {
      method: "POST",
      body: JSON.stringify({ code }),
    },
    token,
  );
}

export async function resendEmail(token: string) {
  return request<{ message: string }>("/auth/resend-email", { method: "POST" }, token);
}

export async function resendPhone(token: string) {
  return request<{ message: string }>("/auth/resend-phone", { method: "POST" }, token);
}

export async function me(token: string) {
  return request<User>("/me", {}, token);
}

export async function updateMe(token: string, name: string) {
  return request<User>(
    "/me",
    {
      method: "PATCH",
      body: JSON.stringify({ name }),
    },
    token,
  );
}

export async function changePassword(token: string, current_password: string, new_password: string) {
  return request<{ message: string }>(
    "/me/password",
    {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    },
    token,
  );
}

export async function listSessions(token: string) {
  return request<SessionItem[]>("/me/sessions", {}, token);
}

export async function revokeSession(token: string, sessionId: number) {
  return request<{ message: string }>(`/me/sessions/${sessionId}`, { method: "DELETE" }, token);
}

export async function listTeams(token: string) {
  return request<Team[]>("/teams", {}, token);
}

export async function createTeam(token: string, payload: { name: string; slug?: string }) {
  return request<Team>(
    "/teams",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
    { timeoutMs: 90_000 },
  );
}

export async function ensurePersonalTeam(token: string) {
  return request<Team>("/teams/personal", { method: "POST" }, token);
}

export async function getTeam(token: string, teamId: number) {
  return request<Team>(`/teams/${teamId}`, {}, token);
}

export async function getTeamMembers(token: string, teamId: number) {
  return request<TeamMember[]>(`/teams/${teamId}/members`, {}, token);
}

export async function inviteTeamMember(token: string, teamId: number, payload: { email?: string; phone?: string; role: string }) {
  return request<TeamInvite>(
    `/teams/${teamId}/invites`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function patchTeamMember(token: string, teamId: number, memberId: number, payload: { role?: string; status?: string }) {
  return request<TeamMember>(
    `/teams/${teamId}/members/${memberId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function removeTeamMember(token: string, teamId: number, memberId: number) {
  return request<{ message: string }>(`/teams/${teamId}/members/${memberId}`, { method: "DELETE" }, token);
}

export async function getTeamAudit(token: string, teamId: number) {
  return request<TeamAudit[]>(`/teams/${teamId}/audit`, {}, token);
}

export async function listTeamConnections(token: string, teamId: number) {
  return request<MarketplaceConnection[]>(`/teams/${teamId}/connections`, {}, token);
}

export async function createTeamConnection(token: string, teamId: number, payload: { provider: string; name: string }) {
  return request<MarketplaceConnection>(
    `/teams/${teamId}/connections`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function patchTeamConnection(
  token: string,
  teamId: number,
  connectionId: number,
  payload: { name?: string; status?: string; is_disabled?: boolean },
) {
  return request<MarketplaceConnection>(
    `/teams/${teamId}/connections/${connectionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteTeamConnection(token: string, teamId: number, connectionId: number) {
  return request<{ message: string }>(`/teams/${teamId}/connections/${connectionId}`, { method: "DELETE" }, token);
}

export async function validateOzonSellerKey(token: string, teamId: number, payload: { client_id: string; api_key: string }) {
  return request<MarketplaceKeyValidation>(
    `/teams/${teamId}/connections/validate/ozon-seller`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function validateOzonPerformanceKey(token: string, teamId: number, payload: { client_id: string; client_secret: string }) {
  return request<MarketplaceKeyValidation>(
    `/teams/${teamId}/connections/validate/ozon-performance`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listConnectionCredentials(token: string, teamId: number, connectionId: number) {
  return request<MarketplaceCredential[]>(`/teams/${teamId}/connections/${connectionId}/credentials`, {}, token);
}

export async function createConnectionCredential(
  token: string,
  teamId: number,
  connectionId: number,
  payload: MarketplaceCredentialPayload,
) {
  return request<MarketplaceCredential>(
    `/teams/${teamId}/connections/${connectionId}/credentials`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function patchConnectionCredential(
  token: string,
  teamId: number,
  connectionId: number,
  credentialId: number,
  payload: MarketplaceCredentialPayload,
) {
  return request<MarketplaceCredential>(
    `/teams/${teamId}/connections/${connectionId}/credentials/${credentialId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteConnectionCredential(token: string, teamId: number, connectionId: number, credentialId: number) {
  return request<{ message: string }>(
    `/teams/${teamId}/connections/${connectionId}/credentials/${credentialId}`,
    { method: "DELETE" },
    token,
  );
}

export async function listConnectionAccess(token: string, teamId: number, connectionId: number) {
  return request<ConnectionAccess[]>(`/teams/${teamId}/connections/${connectionId}/access`, {}, token);
}

export async function createConnectionAccess(
  token: string,
  teamId: number,
  connectionId: number,
  payload: { team_member_id: number; access_mode: string; is_active?: boolean },
) {
  return request<ConnectionAccess>(
    `/teams/${teamId}/connections/${connectionId}/access`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function patchConnectionAccess(
  token: string,
  teamId: number,
  connectionId: number,
  accessId: number,
  payload: { access_mode?: string; is_active?: boolean },
) {
  return request<ConnectionAccess>(
    `/teams/${teamId}/connections/${connectionId}/access/${accessId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteConnectionAccess(token: string, teamId: number, connectionId: number, accessId: number) {
  return request<{ message: string }>(`/teams/${teamId}/connections/${connectionId}/access/${accessId}`, { method: "DELETE" }, token);
}

export async function createAccessScope(
  token: string,
  teamId: number,
  connectionId: number,
  accessId: number,
  payload: { subject_type: string; subject_value: string; is_excluded?: boolean },
) {
  return request<AccessScope>(
    `/teams/${teamId}/connections/${connectionId}/access/${accessId}/scopes`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listAccessScopes(token: string, teamId: number, connectionId: number, accessId: number) {
  return request<AccessScope[]>(`/teams/${teamId}/connections/${connectionId}/access/${accessId}/scopes`, {}, token);
}

export async function patchAccessScope(
  token: string,
  teamId: number,
  connectionId: number,
  accessId: number,
  scopeId: number,
  payload: { subject_type?: string; subject_value?: string; is_excluded?: boolean },
) {
  return request<AccessScope>(
    `/teams/${teamId}/connections/${connectionId}/access/${accessId}/scopes/${scopeId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteAccessScope(token: string, teamId: number, connectionId: number, accessId: number, scopeId: number) {
  return request<{ message: string }>(
    `/teams/${teamId}/connections/${connectionId}/access/${accessId}/scopes/${scopeId}`,
    { method: "DELETE" },
    token,
  );
}

export async function getTeamDashboard(token: string, teamId: number, connectionId?: number | null) {
  const query = connectionId ? `?connection_id=${connectionId}` : "";
  return request<TeamDashboard>(`/teams/${teamId}/dashboard${query}`, {}, token);
}

export async function getAnalyticsProducts(token: string, teamId: number, connectionId: number, limit = 50) {
  return request<AnalyticsProduct[]>(
    `/teams/${teamId}/analytics/products?connection_id=${connectionId}&limit=${limit}`,
    {},
    token,
  );
}

export async function listConnectionProducts(token: string, teamId: number, connectionId: number, limit = 200, onlyCurrent = true) {
  return request<MarketplaceProductItem[]>(
    `/teams/${teamId}/connections/${connectionId}/products?limit=${limit}&only_current=${onlyCurrent ? "true" : "false"}`,
    {},
    token,
  );
}

export async function saveOzonProductMedia(
  token: string,
  teamId: number,
  connectionId: number,
  productRowId: number,
  payload: { image_urls?: string[]; video_urls?: string[]; video_cover_url?: string | null },
) {
  return request<OzonProductMediaSaveResult>(
    `/teams/${teamId}/connections/${connectionId}/products/${productRowId}/media/ozon`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function createOzonProduct(
  token: string,
  teamId: number,
  connectionId: number,
  payload: {
    offer_id: string;
    name: string;
    description?: string | null;
    description_category_id: number;
    type_id: number;
    barcode?: string | null;
    image_urls?: string[];
    video_urls?: string[];
    video_cover_url?: string | null;
    attributes?: Array<Record<string, unknown>>;
    complex_attributes?: Array<Record<string, unknown>>;
    dimension_unit?: string;
    depth?: number;
    width?: number;
    height?: number;
    weight_unit?: string;
    weight?: number;
    price?: string | null;
    old_price?: string | null;
    currency_code?: string;
  },
) {
  return request<OzonProductCreateResult>(
    `/teams/${teamId}/connections/${connectionId}/products/ozon`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function getOzonAttributes(
  token: string,
  teamId: number,
  connectionId: number,
  descriptionCategoryId: number,
  typeId: number,
) {
  return request<OzonAttribute[]>(
    `/teams/${teamId}/connections/${connectionId}/ozon/attributes?description_category_id=${descriptionCategoryId}&type_id=${typeId}`,
    {},
    token,
  );
}

export async function getOzonAttributeValues(
  token: string,
  teamId: number,
  connectionId: number,
  attributeId: number,
  descriptionCategoryId: number,
  typeId: number,
  limit = 50,
) {
  return request<OzonAttributeValue[]>(
    `/teams/${teamId}/connections/${connectionId}/ozon/attributes/${attributeId}/values?description_category_id=${descriptionCategoryId}&type_id=${typeId}&limit=${limit}`,
    {},
    token,
  );
}

export async function refreshOzonContentRating(
  token: string,
  teamId: number,
  connectionId: number,
  payload?: { limit?: number; product_row_ids?: number[]; only_missing?: boolean },
) {
  return request<OzonContentRatingRefreshResult>(
    `/teams/${teamId}/connections/${connectionId}/products/ozon/content-rating`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    },
    token,
  );
}

export async function createAiCardDraft(
  token: string,
  teamId: number,
  connectionId: number,
  productRowId: number,
  payload: {
    current_fields?: Record<string, unknown>;
    image_urls?: string[];
    template_id?: string | null;
    user_prompt?: string | null;
    reference?: Record<string, unknown>;
    goals?: Record<string, unknown>;
  },
) {
  return request<AiCardDraftResult>(
    `/teams/${teamId}/connections/${connectionId}/products/${productRowId}/ai/card-draft`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
    { timeoutMs: 90_000 },
  );
}

export async function generateAiMediaImage(
  token: string,
  teamId: number,
  connectionId: number,
  productRowId: number,
  payload: {
    source_image_url: string;
    prompt: string;
    reference?: Record<string, unknown>;
    output_format?: string;
    size?: string;
  },
) {
  return request<AiMediaGenerateResult>(
    `/teams/${teamId}/connections/${connectionId}/products/${productRowId}/ai/media-image`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
    { timeoutMs: 30_000 },
  );
}

export async function getAiMediaImageStatus(token: string, teamId: number, connectionId: number, productRowId: number, logId: number) {
  return request<AiMediaGenerateResult>(
    `/teams/${teamId}/connections/${connectionId}/products/${productRowId}/ai/media-image/${logId}`,
    {},
    token,
    { timeoutMs: 30_000 },
  );
}

export async function listSyncJobs(token: string, teamId: number, connectionId: number) {
  return request<SyncJob[]>(`/teams/${teamId}/sync-jobs?connection_id=${connectionId}`, {}, token);
}

export async function runConnectionSync(
  token: string,
  teamId: number,
  connectionId: number,
  payload: { dry_run?: boolean; stage?: string },
) {
  return request<SyncJob>(
    `/teams/${teamId}/connections/${connectionId}/sync/run`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function importConnectionCosts(
  token: string,
  teamId: number,
  connectionId: number,
  payload: { file_name: string; total_rows: number; accepted_rows: number; rejected_rows: number },
) {
  return request<CostImport>(
    `/teams/${teamId}/connections/${connectionId}/costs/import`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function agentChat(
  token: string,
  payload: { team_id: number; connection_id?: number; message: string; execute_tool?: boolean; write_mode?: boolean },
) {
  return request<AgentChatResult>(
    "/agent/chat",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function platformMe(token: string) {
  return request<PlatformActor>("/platform/me", {}, token);
}

export async function platformStats(token: string) {
  return request<PlatformStats>("/platform/stats", {}, token);
}

export async function platformUsers(token: string) {
  return request<PlatformUser[]>("/platform/users", {}, token);
}

export async function platformTeams(token: string) {
  return request<PlatformTeam[]>("/platform/teams", {}, token);
}

export async function platformSupportTickets(token: string) {
  return request<Array<{ id?: number; status?: string }>>("/platform/support/tickets", {}, token);
}

export async function platformUpdateSupportTicket(token: string, ticketId: number) {
  return request<{ message: string }>(`/platform/support/tickets/${ticketId}`, { method: "PATCH" }, token);
}

export async function platformAudit(token: string) {
  return request<Array<Record<string, unknown>>>("/platform/audit", {}, token);
}

export async function platformAiLogs(
  token: string,
  params: {
    status?: string;
    operation?: string;
    provider?: string;
    team_id?: string;
    connection_id?: string;
    product_row_id?: string;
    limit?: number;
  } = {},
) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    query.set(key, String(value));
  });
  return request<AiGenerationLog[]>(`/platform/ai/logs${query.toString() ? `?${query.toString()}` : ""}`, {}, token);
}

export async function platformRecommendations(token: string) {
  return request<DashboardRecommendation[]>("/platform/recommendations", {}, token);
}

export async function platformCreateRecommendation(
  token: string,
  payload: {
    title: string;
    body: string;
    cta_label?: string;
    cta_href?: string;
    priority?: number;
    target_marketplace?: string;
    target_team_role?: string;
    is_active?: boolean;
  },
) {
  return request<DashboardRecommendation>(
    "/platform/recommendations",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function platformPatchRecommendation(
  token: string,
  recommendationId: number,
  payload: {
    title?: string;
    body?: string;
    cta_label?: string;
    cta_href?: string;
    priority?: number;
    target_marketplace?: string;
    target_team_role?: string;
    is_active?: boolean;
  },
) {
  return request<DashboardRecommendation>(
    `/platform/recommendations/${recommendationId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function platformDisableRecommendation(token: string, recommendationId: number) {
  return request<{ message: string }>(`/platform/recommendations/${recommendationId}`, { method: "DELETE" }, token);
}

