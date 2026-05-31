from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import decode_access_token
from app.core.platform_policy import has_platform_permission
from app.core.policy import has_permission
from app.models import (
    AccessScope,
    ConnectionAccess,
    ConnectionAccessMode,
    MarketplaceConnection,
    PlatformRoleAssignment,
    SessionModel,
    TeamMember,
    TeamMemberStatus,
    TeamRole,
    User,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> tuple[User, SessionModel]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        session_id = int(payload["sid"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    session = db.get(SessionModel, session_id)
    if session is None or session.user_id != user_id or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")

    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")

    return user, session


def get_current_team_member(
    team_id: int,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamMember:
    user, _ = user_with_session
    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == user.id)
        .filter(TeamMember.status == TeamMemberStatus.active.value)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for this team")
    return membership


def require_team_permission(permission: str, member: TeamMember) -> None:
    if not has_permission(member.role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def get_current_platform_actor(
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    x_platform_role: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PlatformRoleAssignment:
    user, _ = user_with_session
    query = db.query(PlatformRoleAssignment).filter(PlatformRoleAssignment.user_id == user.id).filter(PlatformRoleAssignment.status == "ACTIVE")
    if x_platform_role:
        query = query.filter(PlatformRoleAssignment.role == x_platform_role)
    actor = query.first()
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform access denied")
    return actor


def require_platform_permission(permission: str, actor: PlatformRoleAssignment) -> None:
    if not has_platform_permission(actor.role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform permission denied")


def require_connection_access(
    permission: str,
    connection_id: int,
    member: TeamMember,
    db: Session,
) -> ConnectionAccess | None:
    require_team_permission(permission, member)
    connection = (
        db.query(MarketplaceConnection)
        .filter(MarketplaceConnection.id == connection_id)
        .filter(MarketplaceConnection.team_id == member.team_id)
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    if member.role in {TeamRole.owner.value, TeamRole.admin.value}:
        return None

    access = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.team_id == member.team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .filter(ConnectionAccess.team_member_id == member.id)
        .filter(ConnectionAccess.is_active.is_(True))
        .first()
    )
    if access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Connection access denied")
    if access.access_mode in {ConnectionAccessMode.none.value, ConnectionAccessMode.disabled.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Connection access denied")

    write_permissions = {
        Permission.CONNECTIONS_UPDATE,
        Permission.CONNECTIONS_DELETE,
        Permission.COSTS_IMPORT,
        Permission.SYNC_RUN,
        Permission.RECONCILIATION_RUN,
    }
    if permission in write_permissions and access.access_mode == ConnectionAccessMode.read_only.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only connection access")

    return access


def build_scope_filter(member: TeamMember, connection_id: int, db: Session) -> list[AccessScope]:
    if member.role in {TeamRole.owner.value, TeamRole.admin.value}:
        return []
    access = require_connection_access(Permission.ANALYTICS_READ, connection_id, member, db)
    if access is None:
        return []
    return (
        db.query(AccessScope)
        .filter(AccessScope.team_id == member.team_id)
        .filter(AccessScope.connection_access_id == access.id)
        .order_by(AccessScope.id.asc())
        .all()
    )
