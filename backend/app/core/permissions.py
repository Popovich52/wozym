from __future__ import annotations


class Permission:
    TEAM_MEMBERS_READ = "team.members.read"
    TEAM_MEMBERS_MANAGE = "team.members.manage"
    TEAM_ROLES_MANAGE = "team.roles.manage"
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"
    CONNECTIONS_READ = "connections.read"
    CONNECTIONS_CREATE = "connections.create"
    CONNECTIONS_UPDATE = "connections.update"
    CONNECTIONS_DELETE = "connections.delete"
    CONNECTIONS_SHARE = "connections.share"
    ANALYTICS_READ = "analytics.read"
    ANALYTICS_EXPORT = "analytics.export"
    COSTS_READ = "costs.read"
    COSTS_IMPORT = "costs.import"
    SYNC_READ = "sync.read"
    SYNC_RUN = "sync.run"
    RECONCILIATION_READ = "reconciliation.read"
    RECONCILIATION_RUN = "reconciliation.run"
    AUDIT_READ = "audit.read"
    AGENT_CHAT = "agent.chat"
    AGENT_TOOLS_EXECUTE = "agent.tools.execute"


class PlatformPermission:
    USERS_READ = "platform.users.read"
    TEAMS_READ = "platform.teams.read"
    SUPPORT_TICKETS_MANAGE = "platform.support.tickets.manage"
    AUDIT_READ = "platform.audit.read"
    IMPERSONATION_REQUEST = "platform.impersonation.request"
    SETTINGS_MANAGE = "platform.settings.manage"
