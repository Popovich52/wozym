from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PlatformPermission
from app.deps import get_current_platform_actor, require_platform_permission
from app.models import AiGenerationLog, DashboardRecommendation, Marketplace, MessengerAccountLink, PlatformRoleAssignment, Team, TeamRole, User
from app.schemas import (
    AiGenerationLogOut,
    DashboardRecommendationCreateRequest,
    DashboardRecommendationOut,
    DashboardRecommendationPatchRequest,
    MessageOut,
    PlatformActorOut,
)


router = APIRouter(prefix="/platform", tags=["platform"])


def normalize_optional_marketplace(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    allowed = {item.value for item in Marketplace}
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail="Invalid target_marketplace")
    return normalized


def normalize_optional_team_role(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    allowed = {item.value for item in TeamRole}
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail="Invalid target_team_role")
    return normalized


@router.get("/me", response_model=PlatformActorOut)
def platform_me(actor: PlatformRoleAssignment = Depends(get_current_platform_actor)) -> PlatformActorOut:
    return actor


@router.get("/stats")
def platform_stats(actor: PlatformRoleAssignment = Depends(get_current_platform_actor), db: Session = Depends(get_db)) -> dict[str, int]:
    require_platform_permission(PlatformPermission.TEAMS_READ, actor)
    teams_total = db.query(func.count(Team.id)).scalar() or 0
    users_total = db.query(func.count(User.id)).scalar() or 0
    return {"teams_total": int(teams_total), "users_total": int(users_total)}


@router.get("/users")
def platform_users(actor: PlatformRoleAssignment = Depends(get_current_platform_actor), db: Session = Depends(get_db)) -> list[dict]:
    require_platform_permission(PlatformPermission.USERS_READ, actor)
    rows = db.query(User).order_by(User.id.desc()).limit(200).all()
    user_ids = [row.id for row in rows]
    links_by_user: dict[int, dict[str, str | None]] = {}
    if user_ids:
        links = db.query(MessengerAccountLink).filter(MessengerAccountLink.user_id.in_(user_ids)).all()
        for link in links:
            bucket = links_by_user.setdefault(link.user_id, {"telegram": None, "max": None})
            if link.provider == "telegram":
                bucket["telegram"] = link.handle or link.external_user_id
            if link.provider == "max":
                bucket["max"] = link.handle or link.external_user_id
    payload: list[dict] = []
    for row in rows:
        link_data = links_by_user.get(row.id, {"telegram": None, "max": None})
        payload.append(
            {
                "id": row.id,
                "email": row.email,
                "phone": row.phone,
                "telegram": link_data["telegram"],
                "max": link_data["max"],
                "status": row.status,
                "registered_at": row.created_at.isoformat(),
            }
        )
    return payload


@router.get("/users/{user_id}")
def platform_user_detail(user_id: int, actor: PlatformRoleAssignment = Depends(get_current_platform_actor), db: Session = Depends(get_db)) -> dict:
    require_platform_permission(PlatformPermission.USERS_READ, actor)
    row = db.get(User, user_id)
    if row is None:
        return {"found": False}
    return {
        "found": True,
        "id": row.id,
        "email": row.email,
        "phone": row.phone,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/teams")
def platform_teams(actor: PlatformRoleAssignment = Depends(get_current_platform_actor), db: Session = Depends(get_db)) -> list[dict]:
    require_platform_permission(PlatformPermission.TEAMS_READ, actor)
    rows = db.query(Team).order_by(Team.id.desc()).limit(200).all()
    return [{"id": row.id, "slug": row.slug, "name": row.name, "is_active": row.is_active, "created_at": row.created_at.isoformat()} for row in rows]


@router.get("/teams/{team_id}")
def platform_team_detail(team_id: int, actor: PlatformRoleAssignment = Depends(get_current_platform_actor), db: Session = Depends(get_db)) -> dict:
    require_platform_permission(PlatformPermission.TEAMS_READ, actor)
    row = db.get(Team, team_id)
    if row is None:
        return {"found": False}
    return {"found": True, "id": row.id, "slug": row.slug, "name": row.name, "is_active": row.is_active, "created_at": row.created_at.isoformat()}


@router.get("/support/tickets")
def platform_support_tickets(actor: PlatformRoleAssignment = Depends(get_current_platform_actor)) -> list[dict]:
    require_platform_permission(PlatformPermission.SUPPORT_TICKETS_MANAGE, actor)
    return []


@router.patch("/support/tickets/{ticket_id}", response_model=MessageOut)
def patch_support_ticket(ticket_id: int, actor: PlatformRoleAssignment = Depends(get_current_platform_actor)) -> MessageOut:
    require_platform_permission(PlatformPermission.SUPPORT_TICKETS_MANAGE, actor)
    return MessageOut(message=f"Support ticket {ticket_id} update placeholder")


@router.get("/audit")
def platform_audit(actor: PlatformRoleAssignment = Depends(get_current_platform_actor)) -> list[dict]:
    require_platform_permission(PlatformPermission.AUDIT_READ, actor)
    return []


@router.get("/ai/logs", response_model=list[AiGenerationLogOut])
def platform_ai_logs(
    actor: PlatformRoleAssignment = Depends(get_current_platform_actor),
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, max_length=20),
    operation: str | None = Query(default=None, max_length=80),
    provider: str | None = Query(default=None, max_length=40),
    team_id: int | None = Query(default=None, ge=1),
    connection_id: int | None = Query(default=None, ge=1),
    product_row_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AiGenerationLogOut]:
    require_platform_permission(PlatformPermission.AUDIT_READ, actor)
    query = db.query(AiGenerationLog)
    if status:
        query = query.filter(AiGenerationLog.status == status.strip().lower())
    if operation:
        query = query.filter(AiGenerationLog.operation == operation.strip())
    if provider:
        query = query.filter(AiGenerationLog.provider == provider.strip().lower())
    if team_id is not None:
        query = query.filter(AiGenerationLog.team_id == team_id)
    if connection_id is not None:
        query = query.filter(AiGenerationLog.connection_id == connection_id)
    if product_row_id is not None:
        query = query.filter(AiGenerationLog.product_row_id == product_row_id)
    return query.order_by(AiGenerationLog.created_at.desc(), AiGenerationLog.id.desc()).limit(limit).all()


@router.post("/support/grants/request", response_model=MessageOut)
def support_grant_request(actor: PlatformRoleAssignment = Depends(get_current_platform_actor)) -> MessageOut:
    require_platform_permission(PlatformPermission.SUPPORT_TICKETS_MANAGE, actor)
    return MessageOut(message="Support object grant request placeholder")


@router.get("/recommendations", response_model=list[DashboardRecommendationOut])
def list_dashboard_recommendations(
    actor: PlatformRoleAssignment = Depends(get_current_platform_actor),
    db: Session = Depends(get_db),
) -> list[DashboardRecommendationOut]:
    require_platform_permission(PlatformPermission.SETTINGS_MANAGE, actor)
    rows = db.query(DashboardRecommendation).order_by(DashboardRecommendation.priority.asc(), DashboardRecommendation.id.asc()).all()
    return rows


@router.post("/recommendations", response_model=DashboardRecommendationOut)
def create_dashboard_recommendation(
    payload: DashboardRecommendationCreateRequest,
    actor: PlatformRoleAssignment = Depends(get_current_platform_actor),
    db: Session = Depends(get_db),
) -> DashboardRecommendationOut:
    require_platform_permission(PlatformPermission.SETTINGS_MANAGE, actor)
    row = DashboardRecommendation(
        title=payload.title.strip(),
        body=payload.body.strip(),
        cta_label=payload.cta_label.strip() if payload.cta_label else None,
        cta_href=payload.cta_href.strip() if payload.cta_href else None,
        priority=payload.priority,
        target_marketplace=normalize_optional_marketplace(payload.target_marketplace),
        target_team_role=normalize_optional_team_role(payload.target_team_role),
        is_active=payload.is_active,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/recommendations/{recommendation_id}", response_model=DashboardRecommendationOut)
def patch_dashboard_recommendation(
    recommendation_id: int,
    payload: DashboardRecommendationPatchRequest,
    actor: PlatformRoleAssignment = Depends(get_current_platform_actor),
    db: Session = Depends(get_db),
) -> DashboardRecommendationOut:
    require_platform_permission(PlatformPermission.SETTINGS_MANAGE, actor)
    row = db.get(DashboardRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.body is not None:
        row.body = payload.body.strip()
    if payload.cta_label is not None:
        row.cta_label = payload.cta_label.strip() if payload.cta_label.strip() else None
    if payload.cta_href is not None:
        row.cta_href = payload.cta_href.strip() if payload.cta_href.strip() else None
    if payload.priority is not None:
        row.priority = payload.priority
    if payload.target_marketplace is not None:
        row.target_marketplace = normalize_optional_marketplace(payload.target_marketplace)
    if payload.target_team_role is not None:
        row.target_team_role = normalize_optional_team_role(payload.target_team_role)
    if payload.is_active is not None:
        row.is_active = payload.is_active
    row.updated_by_user_id = actor.user_id
    db.commit()
    db.refresh(row)
    return row


@router.delete("/recommendations/{recommendation_id}", response_model=MessageOut)
def disable_dashboard_recommendation(
    recommendation_id: int,
    actor: PlatformRoleAssignment = Depends(get_current_platform_actor),
    db: Session = Depends(get_db),
) -> MessageOut:
    require_platform_permission(PlatformPermission.SETTINGS_MANAGE, actor)
    row = db.get(DashboardRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    row.is_active = False
    row.updated_by_user_id = actor.user_id
    db.commit()
    return MessageOut(message=f"Recommendation {recommendation_id} disabled")
