from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.policy import ROLE_PERMISSIONS
from app.core.database import get_db
from app.core.permissions import Permission
from app.deps import build_scope_filter, get_current_user, require_connection_access, require_team_permission
from app.models import ConnectionAccessMode, SessionModel, TeamMember, TeamMemberStatus, User
from app.schemas import AgentChatOut, AgentChatRequest
from app.services import add_audit


router = APIRouter(prefix="/agent", tags=["agent"])


def _get_active_member_or_403(db: Session, *, team_id: int, user_id: int) -> TeamMember:
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == user_id)
        .filter(TeamMember.status == TeamMemberStatus.active.value)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=403, detail="Forbidden for this team")
    return member


@router.post("/chat", response_model=AgentChatOut)
def agent_chat(
    payload: AgentChatRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentChatOut:
    user, _session = user_with_session
    member = _get_active_member_or_403(db, team_id=payload.team_id, user_id=user.id)

    permission = Permission.AGENT_TOOLS_EXECUTE if payload.execute_tool else Permission.AGENT_CHAT
    try:
        require_team_permission(permission, member)
        if payload.connection_id is not None:
            connection_permission = Permission.CONNECTIONS_UPDATE if payload.execute_tool and payload.write_mode else Permission.ANALYTICS_READ
            access = require_connection_access(connection_permission, payload.connection_id, member, db)
            if payload.execute_tool and payload.write_mode and access is not None and access.access_mode == ConnectionAccessMode.read_only.value:
                raise HTTPException(status_code=403, detail="Read-only connection access")
    except HTTPException as exc:
        if exc.status_code == 403:
            add_audit(
                db,
                "access.denied",
                user.id,
                request.client.host if request.client else None,
                team_id=payload.team_id,
                connection_id=payload.connection_id,
                resource_type="agent_chat",
                resource_id=str(payload.team_id),
                metadata={
                    "permission": permission,
                    "execute_tool": payload.execute_tool,
                    "write_mode": payload.write_mode,
                },
            )
            db.commit()
        raise

    scopes = []
    if payload.connection_id is not None:
        scopes = build_scope_filter(member, payload.connection_id, db)

    add_audit(
        db,
        "agent.chat.requested",
        user.id,
        request.client.host if request.client else None,
        team_id=payload.team_id,
        connection_id=payload.connection_id,
        resource_type="agent_chat",
        resource_id=str(payload.team_id),
        metadata={
            "execute_tool": payload.execute_tool,
            "write_mode": payload.write_mode,
        },
    )
    db.commit()

    return AgentChatOut(
        message="Agent request accepted",
        context={
            "user_id": user.id,
            "team_id": payload.team_id,
            "team_role": member.role,
            "permissions": sorted(ROLE_PERMISSIONS.get(member.role, set())),
            "required_permission": permission,
            "connection_id": payload.connection_id,
            "scope_count": len(scopes),
            "scopes": [
                {
                    "subject_type": scope.subject_type,
                    "subject_value": scope.subject_value,
                    "is_excluded": scope.is_excluded,
                }
                for scope in scopes
            ],
        },
    )
