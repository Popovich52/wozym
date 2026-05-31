from __future__ import annotations

from app.core.permissions import PlatformPermission
from app.models import PlatformRole


PLATFORM_ROLE_PERMISSIONS: dict[str, set[str]] = {
    PlatformRole.platform_admin.value: {
        PlatformPermission.USERS_READ,
        PlatformPermission.TEAMS_READ,
        PlatformPermission.SUPPORT_TICKETS_MANAGE,
        PlatformPermission.AUDIT_READ,
        PlatformPermission.IMPERSONATION_REQUEST,
        PlatformPermission.SETTINGS_MANAGE,
    },
    PlatformRole.support_admin.value: {
        PlatformPermission.USERS_READ,
        PlatformPermission.TEAMS_READ,
        PlatformPermission.SUPPORT_TICKETS_MANAGE,
        PlatformPermission.AUDIT_READ,
    },
    PlatformRole.support_specialist.value: {
        PlatformPermission.USERS_READ,
        PlatformPermission.TEAMS_READ,
        PlatformPermission.SUPPORT_TICKETS_MANAGE,
    },
}


def has_platform_permission(role: str, permission: str) -> bool:
    return permission in PLATFORM_ROLE_PERMISSIONS.get(role, set())
