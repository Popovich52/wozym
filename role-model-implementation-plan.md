# Role Model Implementation Plan

Updated: 2026-05-30

Goal: build a scalable authorization model for team workspaces, marketplace connections, scoped analytics access, exports, cost imports, sync jobs, and future LangChain agent tools.

## 0. Design Principles

- [x] Keep `User` as identity only, not as a company boundary.
- [x] Use `Team` as the main tenant boundary.
- [x] Keep platform roles separate from client team roles.
- [x] Do not give support roles implicit access to client data.
- [x] Use `TeamMember` for membership, role and lifecycle.
- [x] Use `Permission` checks for actions, not hardcoded role checks across routes.
- [x] Use `ConnectionAccess` for per-connection access.
- [x] Use `AccessScope` for brand/category restrictions.
- [ ] Always filter data by `team_id` and, where applicable, `connection_id`.
- [x] Apply scope filtering in SQL queries before returning rows.
- [ ] Keep subscription/billing limits separate from user permissions.
- [x] Reuse the same policy layer for backend APIs, exports and agent tools.

## 1. Data Model

- [x] Add enum `TeamRole`: `OWNER`, `ADMIN`, `MANAGER`, `ANALYST`, `VIEWER`, `AGENT`.
- [x] Add enum `PlatformRole`: `PLATFORM_ADMIN`, `SUPPORT_ADMIN`, `SUPPORT_SPECIALIST`.
- [x] Add enum `TeamMemberStatus`: `INVITED`, `ACTIVE`, `SUSPENDED`, `REMOVED`.
- [x] Add enum `PlatformRoleStatus`: `ACTIVE`, `SUSPENDED`, `REVOKED`.
- [x] Add enum `ConnectionAccessMode`: `NONE`, `FULL`, `SCOPED`, `READ_ONLY`, `DISABLED`.
- [x] Add enum `ScopeSubjectType`: `BRAND`, `CATEGORY`, `SKU`, `WAREHOUSE`.
- [x] Add model `Team`.
- [x] Add model `TeamMember`.
- [x] Add model `TeamInvite`.
- [x] Add model `RolePermission`.
- [x] Add model `PlatformRoleAssignment`.
- [x] Add model `PlatformAuditEvent`.
- [x] Add placeholder model `SupportObjectGrant` for later object-level permissions.
- [x] Add model `MarketplaceConnection` if not present in the active schema.
- [x] Add model `ConnectionAccess`.
- [x] Add model `AccessScope`.
- [x] Extend `AuditEvent` with `team_id`, `connection_id`, `resource_type`, `resource_id`.
- [x] Add indexes for `team_id`, `user_id`, `connection_id`, `role`, `status`.
- [x] Add unique constraint for one active membership per `team_id + user_id`.

## 2. Permission Catalog

- [x] Define `team.members.read`.
- [x] Define `team.members.manage`.
- [x] Define `team.roles.manage`.
- [x] Define `billing.read`.
- [x] Define `billing.manage`.
- [x] Define `connections.read`.
- [x] Define `connections.create`.
- [x] Define `connections.update`.
- [x] Define `connections.delete`.
- [x] Define `connections.share`.
- [x] Define `analytics.read`.
- [x] Define `analytics.export`.
- [x] Define `costs.read`.
- [x] Define `costs.import`.
- [x] Define `sync.read`.
- [x] Define `sync.run`.
- [x] Define `reconciliation.read`.
- [x] Define `reconciliation.run`.
- [x] Define `audit.read`.
- [x] Define `agent.chat`.
- [x] Define `agent.tools.execute`.

## 3. Role Presets

Client team roles:

- [x] `OWNER`: all permissions, cannot be removed by non-owner.
- [x] `ADMIN`: team operations, connection operations, analytics, sync, costs, audit read.
- [x] `MANAGER`: scoped connection operations, sync run, cost import, analytics read/export if scope allows.
- [x] `ANALYST`: analytics read/export, reconciliation read, no mutation by default.
- [x] `VIEWER`: analytics read only, no export by default.
- [x] `AGENT`: service role, tool-specific permissions only.
- [x] Store role presets in code first, then move to DB if custom roles are needed.

Platform roles:

- [x] `PLATFORM_ADMIN`: full platform administration, global settings, user/team operations, support override workflows.
- [x] `SUPPORT_ADMIN`: support team lead, ticket management, diagnostics, limited operational actions.
- [x] `SUPPORT_SPECIALIST`: support ticket work, read-only diagnostics, customer communication helpers.
- [x] Keep platform roles out of `TeamMember`.
- [x] Require separate platform console session/context for platform actions.
- [ ] Defer concrete object-level support grants to a later phase.

## 4. Backend Policy Layer

- [x] Add `app/core/permissions.py`.
- [x] Add `app/core/policy.py`.
- [x] Add `app/core/platform_policy.py`.
- [x] Add dependency `get_current_team_member`.
- [x] Add dependency `get_current_platform_actor`.
- [x] Add helper `require_permission(permission, team, resource=None)`.
- [x] Add helper `require_platform_permission(permission, resource=None)`.
- [x] Add helper `require_connection_access(permission, connection_id)`.
- [x] Add helper `build_scope_filter(member, connection_id)`.
- [x] Return `403` for valid users without access.
- [ ] Return `404` for resources outside the current team where enumeration risk exists.
- [ ] Add structured error codes: `AUTH_REQUIRED`, `FORBIDDEN`, `TEAM_NOT_FOUND`, `SCOPE_DENIED`.

## 5. Team API

- [x] `POST /teams`.
- [x] `GET /teams`.
- [x] `GET /teams/{team_id}`.
- [x] `PATCH /teams/{team_id}`.
- [x] `GET /teams/{team_id}/members`.
- [x] `POST /teams/{team_id}/invites`.
- [x] `POST /teams/{team_id}/invites/{invite_id}/accept`.
- [x] `PATCH /teams/{team_id}/members/{member_id}`.
- [x] `DELETE /teams/{team_id}/members/{member_id}`.
- [x] `GET /teams/{team_id}/audit`.

## 6. Connection Access API

- [x] `GET /teams/{team_id}/connections/{connection_id}/access`.
- [x] `POST /teams/{team_id}/connections/{connection_id}/access`.
- [x] `PATCH /teams/{team_id}/connections/{connection_id}/access/{access_id}`.
- [x] `DELETE /teams/{team_id}/connections/{connection_id}/access/{access_id}`.
- [x] `POST /teams/{team_id}/connections/{connection_id}/access/{access_id}/scopes`.
- [x] `PATCH /teams/{team_id}/connections/{connection_id}/access/{access_id}/scopes/{scope_id}`.
- [x] `DELETE /teams/{team_id}/connections/{connection_id}/access/{access_id}/scopes/{scope_id}`.

## 6A. Platform Console API

- [x] `GET /platform/me`.
- [x] `GET /platform/users`.
- [x] `GET /platform/users/{user_id}`.
- [x] `GET /platform/teams`.
- [x] `GET /platform/teams/{team_id}`.
- [ ] `GET /platform/connections`.
- [ ] `GET /platform/connections/{connection_id}/status`.
- [x] `GET /platform/support/tickets`.
- [x] `PATCH /platform/support/tickets/{ticket_id}`.
- [x] `GET /platform/audit`.
- [x] `POST /platform/support/grants/request` as a future placeholder.
- [x] Do not expose client analytics rows through platform APIs in this phase.
- [x] Do not allow support impersonation in this phase.

## 7. Existing API Migration

- [x] Add `team_id` path or session context to current `/me` dependent flows where needed.
- [x] Scope marketplace connection APIs by `team_id`.
- [x] Scope analytics APIs by `team_id + connection_id`.
- [x] Scope export APIs by `team_id + connection_id + access scope`.
- [x] Scope sync APIs by `team_id + connection_id`.
- [x] Scope cost import APIs by `team_id + connection_id`.
- [ ] Block dashboard when no team or no accessible connection exists.
- [ ] Ensure plaintext credentials never appear in role/access responses.

## 8. Frontend UI

Client cabinet:

- [x] Add team switcher in app shell.
- [x] Add `/teams` onboarding state for first team creation.
- [x] Add `/teams/[teamId]/members`.
- [x] Add invite member modal.
- [x] Add member role selector.
- [x] Add member status controls.
- [x] Add `/teams/[teamId]/connections/[connectionId]/access`.
- [x] Add full/scoped/read-only access selector.
- [x] Add brand/category scope editor.
- [ ] Add effective access preview.
- [x] Hide or disable UI actions when permission is missing.
- [x] Still enforce all access on backend.

Platform console:

- [x] Add separate route group `/platform`.
- [x] Add platform login/session guard.
- [x] Add platform dashboard.
- [x] Add users list.
- [x] Add teams list.
- [ ] Add connection diagnostics list.
- [x] Add support tickets placeholder.
- [x] Add platform audit page.
- [x] Keep visual and navigation logic separate from client cabinet.

## 9. Audit And Compliance

- [x] Log `team.created`.
- [x] Log `team.member.invited`.
- [x] Log `team.member.accepted`.
- [x] Log `team.member.role_changed`.
- [x] Log `team.member.removed`.
- [x] Log `connection.access.granted`.
- [x] Log `connection.access.updated`.
- [x] Log `connection.access.revoked`.
- [x] Log `scope.created`.
- [x] Log `scope.updated`.
- [x] Log `scope.deleted`.
- [x] Log denied access attempts for sensitive actions.
- [x] Include actor user, target user, team, connection and IP.
- [ ] Log `platform.role.assigned`.
- [ ] Log `platform.role.revoked`.
- [ ] Log `platform.user.viewed`.
- [ ] Log `platform.team.viewed`.
- [ ] Log `platform.connection.diagnosed`.
- [ ] Log `support.ticket.updated`.
- [ ] Log future `support.grant.created`, `support.grant.used`, `support.grant.expired`.

## 10. Agent Layer Readiness

- [x] Pass `user_id`, `team_id`, `role`, `permissions`, `scope` into agent context.
- [x] Add policy check before each tool execution.
- [x] Add read-only tools first.
- [x] Add approval gate for write tools.
- [x] Add audit event for every tool call.
- [x] Add tests proving agent cannot access another team or denied connection.

## 11. Tests

- [x] Owner can invite member.
- [x] Admin can invite member if allowed.
- [x] Analyst cannot invite member.
- [x] Viewer cannot create connection.
- [x] Manager can run sync only for allowed connection.
- [x] Scoped user sees only allowed brand/category data.
- [x] Scoped export contains only allowed rows.
- [x] Removed member cannot access team APIs.
- [x] Suspended member receives `403`.
- [x] Cross-team resource access is denied.
- [x] Audit events are created for IAM changes.
- [x] Agent tool respects the same policy layer.

## 12. Execution Order

- [x] Stage 1: Add migrations and models for `Team`, `TeamMember`, `RolePermission`.
- [x] Stage 2: Add platform role models and platform policy skeleton.
- [x] Stage 3: Add team bootstrap on registration.
- [x] Stage 4: Add policy layer and protect current account endpoints.
- [x] Stage 5: Add team/member APIs and tests.
- [x] Stage 6: Add frontend team switcher and members page.
- [x] Stage 7: Add platform console shell and read-only platform diagnostics.
- [x] Stage 8: Add `ConnectionAccess` and `AccessScope`.
- [x] Stage 9: Apply scope filters to analytics/export APIs.
- [x] Stage 10: Add connection access UI.
- [x] Stage 11: Wire audit and denied-access logging.
- [x] Stage 12: Connect agent endpoint to the policy context.

## 13. Acceptance Criteria

- [x] A registered user automatically gets a default team as `OWNER`.
- [x] Owner can invite a user by email or phone.
- [x] Invited user can accept and enter the team.
- [x] Role changes affect API access immediately.
- [x] Connection access can be granted as full or scoped.
- [x] Scoped users cannot read/export data outside their scope.
- [x] All protected APIs enforce backend authorization.
- [x] Audit trail shows team and access changes.
- [x] Agent tools cannot bypass role or scope checks.
- [x] Platform roles are assigned outside client teams.
- [x] Platform console is separated from client cabinet.
- [x] Support roles cannot access client object data without a future explicit grant mechanism.
