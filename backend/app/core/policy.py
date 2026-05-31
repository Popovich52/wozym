from __future__ import annotations

from app.core.permissions import Permission
from app.models import TeamRole


ROLE_PERMISSIONS: dict[str, set[str]] = {
    TeamRole.owner.value: {
        Permission.TEAM_MEMBERS_READ,
        Permission.TEAM_MEMBERS_MANAGE,
        Permission.TEAM_ROLES_MANAGE,
        Permission.BILLING_READ,
        Permission.BILLING_MANAGE,
        Permission.CONNECTIONS_READ,
        Permission.CONNECTIONS_CREATE,
        Permission.CONNECTIONS_UPDATE,
        Permission.CONNECTIONS_DELETE,
        Permission.CONNECTIONS_SHARE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.COSTS_READ,
        Permission.COSTS_IMPORT,
        Permission.SYNC_READ,
        Permission.SYNC_RUN,
        Permission.RECONCILIATION_READ,
        Permission.RECONCILIATION_RUN,
        Permission.AUDIT_READ,
        Permission.AGENT_CHAT,
        Permission.AGENT_TOOLS_EXECUTE,
    },
    TeamRole.admin.value: {
        Permission.TEAM_MEMBERS_READ,
        Permission.TEAM_MEMBERS_MANAGE,
        Permission.TEAM_ROLES_MANAGE,
        Permission.CONNECTIONS_READ,
        Permission.CONNECTIONS_CREATE,
        Permission.CONNECTIONS_UPDATE,
        Permission.CONNECTIONS_DELETE,
        Permission.CONNECTIONS_SHARE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.COSTS_READ,
        Permission.COSTS_IMPORT,
        Permission.SYNC_READ,
        Permission.SYNC_RUN,
        Permission.RECONCILIATION_READ,
        Permission.RECONCILIATION_RUN,
        Permission.AUDIT_READ,
        Permission.AGENT_CHAT,
        Permission.AGENT_TOOLS_EXECUTE,
    },
    TeamRole.manager.value: {
        Permission.CONNECTIONS_READ,
        Permission.CONNECTIONS_UPDATE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.COSTS_READ,
        Permission.COSTS_IMPORT,
        Permission.SYNC_READ,
        Permission.SYNC_RUN,
        Permission.RECONCILIATION_READ,
        Permission.RECONCILIATION_RUN,
        Permission.AGENT_CHAT,
    },
    TeamRole.analyst.value: {
        Permission.CONNECTIONS_READ,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.COSTS_READ,
        Permission.SYNC_READ,
        Permission.RECONCILIATION_READ,
        Permission.AGENT_CHAT,
    },
    TeamRole.viewer.value: {
        Permission.CONNECTIONS_READ,
        Permission.ANALYTICS_READ,
        Permission.COSTS_READ,
        Permission.SYNC_READ,
        Permission.RECONCILIATION_READ,
    },
    TeamRole.agent.value: {
        Permission.ANALYTICS_READ,
        Permission.AGENT_CHAT,
        Permission.AGENT_TOOLS_EXECUTE,
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
