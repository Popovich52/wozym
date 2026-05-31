from __future__ import annotations

import re
import csv
import io
import time
import ipaddress
from datetime import timedelta, datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import generate_email_token, hash_token, normalize_email, normalize_phone
from app.core.config import settings
from app.deps import build_scope_filter, get_current_team_member, get_current_user, require_connection_access, require_team_permission
from app.ai_product_cards import create_ai_media_image_job, generate_ai_card_draft, run_ai_media_image_job
from app.marketplace_sync import sync_products_for_connection
from app.models import (
    AnalyticsProductFact,
    AccessScope,
    AiGenerationLog,
    AiGenerationStatus,
    AuditEvent,
    CostImport,
    ConnectionAccess,
    ConnectionAccessMode,
    ConnectionStatus,
    DashboardRecommendation,
    CredentialAuthScheme,
    Marketplace,
    MarketplaceConnection,
    MarketplaceConnectionCredential,
    MarketplaceProduct,
    SyncJob,
    SyncDomain,
    SyncJobStatus,
    ScopeSubjectType,
    SessionModel,
    Team,
    TeamInvite,
    TeamMember,
    TeamMemberStatus,
    TeamRole,
    User,
)
from app.schemas import (
    AccessScopeCreateRequest,
    AccessScopeOut,
    AccessScopePatchRequest,
    AiCardDraftOut,
    AiCardDraftRequest,
    AiMediaGenerateOut,
    AiMediaGenerateRequest,
    AnalyticsProductOut,
    AuditEventOut,
    CostImportOut,
    CostImportRequest,
    ConnectionAccessCreateRequest,
    ConnectionAccessOut,
    ConnectionAccessPatchRequest,
    DashboardOut,
    DashboardRecommendationOut,
    MarketplaceConnectionCreateRequest,
    MarketplaceCredentialCreateRequest,
    MarketplaceCredentialOut,
    MarketplaceCredentialPatchRequest,
    MarketplaceKeyValidationOut,
    MarketplaceProductOut,
    OzonPerformanceKeyValidationRequest,
    OzonAttributeOut,
    OzonAttributeValueOut,
    OzonContentRatingConditionOut,
    OzonContentRatingGroupOut,
    OzonContentRatingImproveAttributeOut,
    OzonContentRatingItemOut,
    OzonContentRatingRefreshOut,
    OzonContentRatingRefreshRequest,
    OzonProductCreateOut,
    OzonProductCreateRequest,
    OzonProductMediaSaveOut,
    OzonProductMediaSaveRequest,
    OzonSellerKeyValidationRequest,
    MarketplaceConnectionOut,
    MarketplaceConnectionPatchRequest,
    MessageOut,
    SyncJobOut,
    SyncRunRequest,
    TeamCreateRequest,
    TeamInviteCreateRequest,
    TeamInviteOut,
    TeamMemberOut,
    TeamMemberPatchRequest,
    TeamOut,
    TeamPatchRequest,
)
from app.services import add_audit


router = APIRouter(prefix="/teams", tags=["teams"])
slug_re = re.compile(r"[^a-z0-9]+")


def normalize_slug(value: str) -> str:
    return slug_re.sub("-", value.strip().lower()).strip("-")[:64]


def parse_role(value: str) -> str:
    role = value.strip().upper()
    allowed = {item.value for item in TeamRole}
    if role not in allowed:
        raise HTTPException(status_code=422, detail="Invalid role")
    return role


def parse_status(value: str) -> str:
    status = value.strip().upper()
    allowed = {item.value for item in TeamMemberStatus}
    if status not in allowed:
        raise HTTPException(status_code=422, detail="Invalid status")
    return status


def parse_access_mode(value: str) -> str:
    mode = value.strip().upper()
    allowed = {item.value for item in ConnectionAccessMode}
    if mode not in allowed:
        raise HTTPException(status_code=422, detail="Invalid access mode")
    return mode


def parse_scope_subject_type(value: str) -> str:
    subject_type = value.strip().upper()
    allowed = {item.value for item in ScopeSubjectType}
    if subject_type not in allowed:
        raise HTTPException(status_code=422, detail="Invalid scope subject type")
    return subject_type


def parse_marketplace(value: str) -> str:
    provider = value.strip().upper()
    allowed = {item.value for item in Marketplace}
    if provider not in allowed:
        raise HTTPException(status_code=422, detail="Invalid marketplace provider")
    return provider


def parse_connection_status(value: str) -> str:
    status = value.strip().upper()
    allowed = {item.value for item in ConnectionStatus}
    if status not in allowed:
        raise HTTPException(status_code=422, detail="Invalid connection status")
    return status


def parse_credential_auth_scheme(value: str) -> str:
    scheme = value.strip().upper()
    allowed = {item.value for item in CredentialAuthScheme}
    if scheme not in allowed:
        raise HTTPException(status_code=422, detail="Invalid credential auth scheme")
    return scheme


def normalize_credential_kind(value: str) -> str:
    kind = value.strip().upper()
    if not kind:
        raise HTTPException(status_code=422, detail="Invalid credential kind")
    return kind


def is_expired(value: datetime) -> bool:
    now_utc = datetime.now(tz=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc) <= now_utc
    return value <= now_utc


def get_team_connection_or_404(db: Session, team_id: int, connection_id: int) -> MarketplaceConnection:
    connection = (
        db.query(MarketplaceConnection)
        .filter(MarketplaceConnection.id == connection_id)
        .filter(MarketplaceConnection.team_id == team_id)
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


def get_active_connection_credential(db: Session, connection_id: int) -> MarketplaceConnectionCredential | None:
    return (
        db.query(MarketplaceConnectionCredential)
        .filter(MarketplaceConnectionCredential.connection_id == connection_id)
        .filter(MarketplaceConnectionCredential.is_active.is_(True))
        .order_by(MarketplaceConnectionCredential.is_primary.desc(), MarketplaceConnectionCredential.id.asc())
        .first()
    )


def normalize_media_urls(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = (value or "").strip()
        if not candidate:
            continue
        lower = candidate.lower()
        is_http = lower.startswith("http://") or lower.startswith("https://")
        is_data = lower.startswith("data:image/") or lower.startswith("data:video/")
        if not (is_http or is_data):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def is_non_public_media_url(value: str) -> bool:
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def rewrite_local_ai_asset_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.path.startswith("/ai-assets/"):
        return value
    hostname = (parsed.hostname or "").strip().lower()
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return value
    public_api_url = settings.api_url.rstrip("/")
    public_host = (urlparse(public_api_url).hostname or "").strip().lower()
    if not public_api_url or public_host in {"localhost", "127.0.0.1", "::1"}:
        return value
    return f"{public_api_url}{parsed.path}"


def rewrite_local_ai_asset_urls(values: list[str]) -> list[str]:
    return [rewrite_local_ai_asset_url(value) for value in values]


def assert_media_urls_are_public(urls: list[str], *, field_name: str) -> None:
    blocked = [url for url in urls if is_non_public_media_url(url)]
    if blocked:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{field_name}: Ozon загружает изображения по URL со своей стороны, поэтому локальные ссылки "
                f"localhost/127.0.0.1/private IP недоступны. Опубликуйте AI asset в S3/CDN/публичном storage "
                f"или задайте публичный API_URL. Пример недоступной ссылки: {blocked[0][:160]}"
            ),
        )


def log_access_denied(
    db: Session,
    *,
    user_id: int,
    request: Request,
    team_id: int,
    permission: str,
    connection_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    target_user_id: int | None = None,
    extra_meta: dict | None = None,
) -> None:
    metadata = {"permission": permission}
    if target_user_id is not None:
        metadata["target_user_id"] = target_user_id
    if extra_meta:
        metadata.update(extra_meta)
    add_audit(
        db,
        "access.denied",
        user_id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
    )
    db.commit()


def enforce_team_permission(
    *,
    db: Session,
    request: Request,
    member: TeamMember,
    permission: str,
    team_id: int,
    connection_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    target_user_id: int | None = None,
    extra_meta: dict | None = None,
) -> None:
    try:
        require_team_permission(permission, member)
    except HTTPException as exc:
        if exc.status_code == 403:
            log_access_denied(
                db,
                user_id=member.user_id,
                request=request,
                team_id=team_id,
                permission=permission,
                connection_id=connection_id,
                resource_type=resource_type,
                resource_id=resource_id,
                target_user_id=target_user_id,
                extra_meta=extra_meta,
            )
        raise


def enforce_connection_permission(
    *,
    db: Session,
    request: Request,
    member: TeamMember,
    permission: str,
    team_id: int,
    connection_id: int,
    resource_type: str | None = None,
    resource_id: str | None = None,
    target_user_id: int | None = None,
    extra_meta: dict | None = None,
) -> ConnectionAccess | None:
    try:
        return require_connection_access(permission, connection_id, member, db)
    except HTTPException as exc:
        if exc.status_code == 403:
            log_access_denied(
                db,
                user_id=member.user_id,
                request=request,
                team_id=team_id,
                permission=permission,
                connection_id=connection_id,
                resource_type=resource_type,
                resource_id=resource_id or str(connection_id),
                target_user_id=target_user_id,
                extra_meta=extra_meta,
            )
        raise


def _deprecated_log_access_denied_signature_guard(
    db: Session,
    *,
    user_id: int,
    request: Request,
    team_id: int,
    permission: str,
) -> None:
    # Kept to ease transition for local branches if this helper was imported elsewhere.
    log_access_denied(db, user_id=user_id, request=request, team_id=team_id, permission=permission)


def apply_product_scopes(query, scopes: list[AccessScope]):
    includes: dict[str, set[str]] = {}
    excludes: dict[str, set[str]] = {}
    for scope in scopes:
        target = excludes if scope.is_excluded else includes
        target.setdefault(scope.subject_type, set()).add(scope.subject_value)

    field_map = {
        ScopeSubjectType.brand.value: AnalyticsProductFact.brand,
        ScopeSubjectType.category.value: AnalyticsProductFact.category,
        ScopeSubjectType.sku.value: AnalyticsProductFact.sku,
        ScopeSubjectType.warehouse.value: AnalyticsProductFact.warehouse,
    }
    for subject_type, field in field_map.items():
        allowed = includes.get(subject_type, set())
        denied = excludes.get(subject_type, set())
        if allowed:
            query = query.filter(field.in_(allowed))
        if denied:
            query = query.filter(~field.in_(denied))
    return query


def select_dashboard_recommendations(
    db: Session,
    *,
    team_role: str,
    connection_provider: str | None,
    limit: int = 8,
) -> list[DashboardRecommendation]:
    rows = (
        db.query(DashboardRecommendation)
        .filter(DashboardRecommendation.is_active.is_(True))
        .order_by(DashboardRecommendation.priority.asc(), DashboardRecommendation.id.asc())
        .all()
    )
    result: list[DashboardRecommendation] = []
    for row in rows:
        if row.target_team_role and row.target_team_role != team_role:
            continue
        if row.target_marketplace and connection_provider and row.target_marketplace != connection_provider:
            continue
        result.append(row)
        if len(result) >= limit:
            break
    return result


@router.post("", response_model=TeamOut)
def create_team(
    payload: TeamCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamOut:
    user, _ = user_with_session
    requested = payload.slug or payload.name
    slug = normalize_slug(requested)
    if not slug:
        raise HTTPException(status_code=422, detail="Invalid team slug")

    candidate = slug
    suffix = 2
    while db.execute(select(Team).where(Team.slug == candidate)).scalar_one_or_none() is not None:
        candidate = f"{slug}-{suffix}"
        suffix += 1

    team = Team(
        slug=candidate,
        name=payload.name.strip(),
        is_active=True,
        created_by_user_id=user.id,
    )
    db.add(team)
    db.flush()
    db.add(
        TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=TeamRole.owner.value,
            status=TeamMemberStatus.active.value,
            invited_by_user_id=user.id,
        )
    )
    add_audit(
        db,
        "team.created",
        user.id,
        request.client.host if request.client else None,
        team_id=team.id,
        resource_type="team",
        resource_id=str(team.id),
    )
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=list[TeamOut])
def list_teams(user_with_session: tuple[User, SessionModel] = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TeamOut]:
    user, _ = user_with_session
    teams = (
        db.query(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(TeamMember.user_id == user.id)
        .filter(TeamMember.status == TeamMemberStatus.active.value)
        .order_by(Team.id.asc())
        .all()
    )
    return teams


@router.post("/personal", response_model=TeamOut)
def ensure_personal_team(
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamOut:
    user, _ = user_with_session
    personal_slug = f"user-{user.id}-personal"
    existing = (
        db.query(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(Team.slug == personal_slug)
        .filter(TeamMember.user_id == user.id)
        .filter(TeamMember.status == TeamMemberStatus.active.value)
        .first()
    )
    if existing is not None and existing.is_active:
        return existing

    candidate = personal_slug
    suffix = 2
    while db.execute(select(Team).where(Team.slug == candidate)).scalar_one_or_none() is not None:
        candidate = f"{personal_slug}-{suffix}"
        suffix += 1

    team = Team(
        slug=candidate,
        name="Личное пространство",
        is_active=True,
        created_by_user_id=user.id,
    )
    db.add(team)
    db.flush()
    db.add(
        TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=TeamRole.owner.value,
            status=TeamMemberStatus.active.value,
            invited_by_user_id=user.id,
        )
    )
    add_audit(
        db,
        "team.personal.created",
        user.id,
        request.client.host if request.client else None,
        team_id=team.id,
        resource_type="team",
        resource_id=str(team.id),
    )
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> TeamOut:
    _user, _session = user_with_session
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.TEAM_MEMBERS_READ, team_id=team_id, resource_type="team", resource_id=str(team_id))
    team = db.get(Team, team_id)
    if team is None or not team.is_active:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.patch("/{team_id}", response_model=TeamOut)
def patch_team(
    team_id: int,
    payload: TeamPatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> TeamOut:
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.TEAM_MEMBERS_MANAGE, team_id=team_id, resource_type="team", resource_id=str(team_id))
    team = db.get(Team, team_id)
    if team is None or not team.is_active:
        raise HTTPException(status_code=404, detail="Team not found")
    team.name = payload.name.strip()
    user, _ = user_with_session
    add_audit(
        db,
        "team.updated",
        user.id,
        request.client.host if request.client else None,
        team_id=team.id,
        resource_type="team",
        resource_id=str(team.id),
    )
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}/members", response_model=list[TeamMemberOut])
def list_team_members(
    team_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[TeamMemberOut]:
    _user, _session = user_with_session
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.TEAM_MEMBERS_READ, team_id=team_id, resource_type="team", resource_id=str(team_id))
    members = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.status != TeamMemberStatus.removed.value)
        .order_by(TeamMember.id.asc())
        .all()
    )
    return members


@router.post("/{team_id}/invites", response_model=TeamInviteOut)
def create_team_invite(
    team_id: int,
    payload: TeamInviteCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> TeamInviteOut:
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.TEAM_MEMBERS_MANAGE, team_id=team_id, resource_type="team", resource_id=str(team_id))
    user, _ = user_with_session

    email = normalize_email(payload.email) if payload.email else None
    phone = normalize_phone(payload.phone) if payload.phone else None
    if not email and not phone:
        raise HTTPException(status_code=422, detail="Either email or phone is required")
    role = parse_role(payload.role)
    if role == TeamRole.owner.value:
        raise HTTPException(status_code=422, detail="Owner invite is not allowed")

    token = generate_email_token()
    invite = TeamInvite(
        team_id=team_id,
        email=email,
        phone=phone,
        role=role,
        token_hash=hash_token(token),
        status=TeamMemberStatus.invited.value,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
        invited_by_user_id=user.id,
    )
    db.add(invite)
    db.flush()
    add_audit(
        db,
        "team.member.invited",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        resource_type="team_invite",
        resource_id=str(invite.id),
        metadata={"email": email, "phone": phone, "role": role},
    )
    db.commit()
    db.refresh(invite)
    return invite


@router.post("/{team_id}/invites/{invite_id}/accept", response_model=MessageOut)
def accept_team_invite(
    team_id: int,
    invite_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, _ = user_with_session
    invite = db.get(TeamInvite, invite_id)
    if invite is None or invite.team_id != team_id:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.status != TeamMemberStatus.invited.value:
        raise HTTPException(status_code=400, detail="Invite is not active")
    if is_expired(invite.expires_at):
        raise HTTPException(status_code=400, detail="Invite expired")
    if invite.email and invite.email != user.email:
        raise HTTPException(status_code=403, detail="Invite recipient mismatch")
    if invite.phone and invite.phone != user.phone:
        raise HTTPException(status_code=403, detail="Invite recipient mismatch")

    existing = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == user.id)
        .first()
    )
    if existing is not None and existing.status == TeamMemberStatus.active.value:
        raise HTTPException(status_code=409, detail="Already a team member")

    if existing is None:
        db.add(
            TeamMember(
                team_id=team_id,
                user_id=user.id,
                role=invite.role,
                status=TeamMemberStatus.active.value,
                invited_by_user_id=invite.invited_by_user_id,
            )
        )
    else:
        existing.role = invite.role
        existing.status = TeamMemberStatus.active.value
        existing.invited_by_user_id = invite.invited_by_user_id

    invite.status = TeamMemberStatus.active.value
    add_audit(
        db,
        "team.member.accepted",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        resource_type="team_invite",
        resource_id=str(invite.id),
    )
    db.commit()
    return MessageOut(message="Invite accepted")


@router.patch("/{team_id}/members/{member_id}", response_model=TeamMemberOut)
def patch_team_member(
    team_id: int,
    member_id: int,
    payload: TeamMemberPatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    actor_member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> TeamMemberOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=actor_member,
        permission=Permission.TEAM_MEMBERS_MANAGE,
        team_id=team_id,
        resource_type="team_member",
        resource_id=str(member_id),
    )
    target = db.get(TeamMember, member_id)
    if target is None or target.team_id != team_id:
        raise HTTPException(status_code=404, detail="Team member not found")

    actor_is_owner = actor_member.role == TeamRole.owner.value
    target_is_owner = target.role == TeamRole.owner.value
    if target_is_owner and not actor_is_owner:
        raise HTTPException(status_code=403, detail="Only owner can edit owner membership")

    if payload.role is not None:
        next_role = parse_role(payload.role)
        if next_role == TeamRole.owner.value and not actor_is_owner:
            raise HTTPException(status_code=403, detail="Only owner can assign owner role")
        target.role = next_role

    if payload.status is not None:
        next_status = parse_status(payload.status)
        if target_is_owner and next_status != TeamMemberStatus.active.value:
            owners_total = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == team_id)
                .filter(TeamMember.role == TeamRole.owner.value)
                .filter(TeamMember.status == TeamMemberStatus.active.value)
                .count()
            )
            if owners_total <= 1:
                raise HTTPException(status_code=409, detail="Cannot suspend the last active owner")
        target.status = next_status

    user, _ = user_with_session
    add_audit(
        db,
        "team.member.role_changed",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        resource_type="team_member",
        resource_id=str(member_id),
        metadata={"role": target.role, "status": target.status},
    )
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{team_id}/members/{member_id}", response_model=MessageOut)
def delete_team_member(
    team_id: int,
    member_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    actor_member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MessageOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=actor_member,
        permission=Permission.TEAM_MEMBERS_MANAGE,
        team_id=team_id,
        resource_type="team_member",
        resource_id=str(member_id),
    )
    target = db.get(TeamMember, member_id)
    if target is None or target.team_id != team_id:
        raise HTTPException(status_code=404, detail="Team member not found")
    if target.user_id == actor_member.user_id:
        raise HTTPException(status_code=400, detail="Use role/status update for current member")
    if target.role == TeamRole.owner.value:
        owners_total = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team_id)
            .filter(TeamMember.role == TeamRole.owner.value)
            .filter(TeamMember.status == TeamMemberStatus.active.value)
            .count()
        )
        if owners_total <= 1:
            raise HTTPException(status_code=409, detail="Cannot remove the last active owner")
    target.status = TeamMemberStatus.removed.value
    user, _ = user_with_session
    add_audit(
        db,
        "team.member.removed",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        resource_type="team_member",
        resource_id=str(member_id),
    )
    db.commit()
    return MessageOut(message="Member removed")


@router.get("/{team_id}/analytics/products", response_model=list[AnalyticsProductOut])
def get_analytics_products(
    team_id: int,
    connection_id: int = Query(..., ge=1),
    limit: int = Query(default=200, ge=1, le=1000),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[AnalyticsProductOut]:
    _user, _session = user_with_session
    access = enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="analytics_products",
        resource_id=str(connection_id),
    )

    query = (
        db.query(AnalyticsProductFact)
        .filter(AnalyticsProductFact.team_id == team_id)
        .filter(AnalyticsProductFact.connection_id == connection_id)
        .order_by(AnalyticsProductFact.id.asc())
    )
    if access is not None and access.access_mode == ConnectionAccessMode.scoped.value:
        scopes = build_scope_filter(member, connection_id, db)
        if not scopes:
            return []
        query = apply_product_scopes(query, scopes)

    return query.limit(limit).all()


@router.get("/{team_id}/connections/{connection_id}/products", response_model=list[MarketplaceProductOut])
def list_connection_products(
    team_id: int,
    connection_id: int,
    only_current: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[MarketplaceProduct]:
    _user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_products",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    try:
        query = (
            db.query(MarketplaceProduct)
            .filter(MarketplaceProduct.connection_id == connection_id)
            .filter(MarketplaceProduct.provider == connection.provider)
            .order_by(MarketplaceProduct.updated_at.desc(), MarketplaceProduct.id.desc())
        )
        if only_current:
            query = query.filter(MarketplaceProduct.is_current.is_(True))
        return query.limit(limit).all()
    except (OperationalError, ProgrammingError):
        # Keep dashboard stable when runtime DB schema is behind app model.
        return []


@router.post("/{team_id}/connections/{connection_id}/products/{product_row_id}/media/ozon", response_model=OzonProductMediaSaveOut)
def save_ozon_product_media(
    team_id: int,
    connection_id: int,
    product_row_id: int,
    payload: OzonProductMediaSaveRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> OzonProductMediaSaveOut:
    user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product_media",
        resource_id=str(product_row_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if connection.provider != Marketplace.ozon.value:
        raise HTTPException(status_code=422, detail="Media save endpoint is currently available only for Ozon")

    credential = get_active_connection_credential(db, connection_id)
    if credential is None or not credential.client_id_plain or not credential.api_key_plain:
        raise HTTPException(status_code=422, detail="Нет активного Ozon Seller ключа для сохранения медиа")

    row = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.id == product_row_id)
        .filter(MarketplaceProduct.connection_id == connection_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_id_raw = (row.external_product_id or "").strip()
    try:
        product_id = int(product_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="У товара нет корректного product_id для Ozon API")
    if product_id <= 0:
        raise HTTPException(status_code=422, detail="У товара нет корректного product_id для Ozon API")

    offer_id = (row.external_offer_id or "").strip()
    if not offer_id:
        raise HTTPException(status_code=422, detail="У товара нет offer_id для Ozon API")

    image_urls = rewrite_local_ai_asset_urls(normalize_media_urls(payload.image_urls))
    video_urls = rewrite_local_ai_asset_urls(normalize_media_urls(payload.video_urls))
    assert_media_urls_are_public(image_urls, field_name="image_urls")
    assert_media_urls_are_public(video_urls, field_name="video_urls")
    video_cover_url = rewrite_local_ai_asset_url((payload.video_cover_url or "").strip())
    if video_cover_url:
        lower_cover = video_cover_url.lower()
        is_http = lower_cover.startswith("http://") or lower_cover.startswith("https://")
        is_data = lower_cover.startswith("data:image/") or lower_cover.startswith("data:video/")
        if not (is_http or is_data):
            raise HTTPException(status_code=422, detail="video_cover_url должен быть абсолютной ссылкой или data URL")
    if video_cover_url and video_cover_url.startswith("data:video/"):
        raise HTTPException(status_code=422, detail="video_cover_url должен указывать на изображение, а не на видео")
    if video_cover_url:
        assert_media_urls_are_public([video_cover_url], field_name="video_cover_url")

    task_ids: list[int] = []
    cover_applied = False
    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }

    if video_cover_url:
        images_for_cover = [video_cover_url]
        for url in image_urls:
            if url != video_cover_url:
                images_for_cover.append(url)
        image_urls = images_for_cover
        cover_applied = True

    try:
        with httpx.Client(timeout=20.0) as client:
            if image_urls:
                pictures_payload = {
                    "product_id": product_id,
                    "images": image_urls,
                }
                pictures_response = client.post(
                    "https://api-seller.ozon.ru/v1/product/pictures/import",
                    headers=headers,
                    json=pictures_payload,
                )
                if pictures_response.status_code != 200:
                    message = "Не удалось сохранить фото в Ozon"
                    try:
                        message = str((pictures_response.json() or {}).get("message") or message)
                    except ValueError:
                        if pictures_response.text:
                            message = pictures_response.text[:300]
                    raise HTTPException(status_code=422, detail=message)

            if video_urls:
                video_values = [{"value": value} for value in video_urls]
                video_payload = {
                    "items": [
                        {
                            "offer_id": offer_id,
                            "complex_attributes": [
                                {
                                    "id": 21845,
                                    "complex_id": 100002,
                                    "values": video_values,
                                }
                            ],
                        }
                    ]
                }
                video_response = client.post(
                    "https://api-seller.ozon.ru/v1/product/attributes/update",
                    headers=headers,
                    json=video_payload,
                )
                if video_response.status_code != 200:
                    message = "Не удалось сохранить видео в Ozon"
                    try:
                        message = str((video_response.json() or {}).get("message") or message)
                    except ValueError:
                        if video_response.text:
                            message = video_response.text[:300]
                    raise HTTPException(status_code=422, detail=message)
                try:
                    task_id = int((video_response.json() or {}).get("task_id") or 0)
                    if task_id > 0:
                        task_ids.append(task_id)
                except (TypeError, ValueError):
                    pass
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с Ozon: {exc.__class__.__name__}") from exc

    if image_urls:
        row.image_urls = image_urls
    if video_urls:
        row.video_urls = video_urls
    row.updated_at = datetime.now(tz=timezone.utc)

    add_audit(
        db,
        "product.media.saved.ozon",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product",
        resource_id=str(product_row_id),
        metadata={
            "images_count": len(image_urls),
            "videos_count": len(video_urls),
            "cover_applied": cover_applied,
            "task_ids": task_ids,
        },
    )
    db.commit()

    return OzonProductMediaSaveOut(
        saved_images=len(image_urls),
        saved_videos=len(video_urls),
        cover_applied=cover_applied,
        task_ids=task_ids,
        message="Медиа отправлены в Ozon. Изменения могут примениться не мгновенно.",
    )


@router.post("/{team_id}/connections/{connection_id}/products/ozon", response_model=OzonProductCreateOut)
def create_ozon_product(
    team_id: int,
    connection_id: int,
    payload: OzonProductCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> OzonProductCreateOut:
    user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product_create",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if connection.provider != Marketplace.ozon.value:
        raise HTTPException(status_code=422, detail="Создание позиции через этот endpoint доступно только для Ozon")

    credential = get_active_connection_credential(db, connection_id)
    if credential is None or not credential.client_id_plain or not credential.api_key_plain:
        raise HTTPException(status_code=422, detail="Нет активного Ozon Seller ключа для создания позиции")

    image_urls = rewrite_local_ai_asset_urls(normalize_media_urls(payload.image_urls))
    video_urls = rewrite_local_ai_asset_urls(normalize_media_urls(payload.video_urls))
    assert_media_urls_are_public(image_urls, field_name="image_urls")
    assert_media_urls_are_public(video_urls, field_name="video_urls")
    video_cover_url = rewrite_local_ai_asset_url((payload.video_cover_url or "").strip())
    if video_cover_url:
        lower_cover = video_cover_url.lower()
        if not (lower_cover.startswith("http://") or lower_cover.startswith("https://") or lower_cover.startswith("data:image/")):
            raise HTTPException(status_code=422, detail="Обложка видео должна быть URL изображения или data:image")
        assert_media_urls_are_public([video_cover_url], field_name="video_cover_url")
        if video_cover_url not in image_urls:
            image_urls = [video_cover_url, *image_urls]
        else:
            image_urls = [video_cover_url, *[item for item in image_urls if item != video_cover_url]]

    if not image_urls:
        raise HTTPException(status_code=422, detail="Для создания позиции нужно добавить хотя бы одно фото")
    if not payload.attributes:
        raise HTTPException(status_code=422, detail="Нужно передать attributes (обязательные атрибуты категории)")

    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }

    attributes = payload.attributes if isinstance(payload.attributes, list) else []
    complex_attributes = payload.complex_attributes if isinstance(payload.complex_attributes, list) else []
    if video_urls:
        complex_attributes = [
            *complex_attributes,
            {
                "id": 21845,
                "complex_id": 100002,
                "values": [{"value": url} for url in video_urls],
            },
        ]

    item_payload: dict = {
        "offer_id": payload.offer_id.strip(),
        "name": payload.name.strip(),
        "description_category_id": payload.description_category_id,
        "type_id": payload.type_id,
        "barcode": (payload.barcode or "").strip(),
        "images": image_urls,
        "attributes": attributes,
        "complex_attributes": complex_attributes,
        "dimension_unit": payload.dimension_unit,
        "depth": payload.depth,
        "width": payload.width,
        "height": payload.height,
        "weight_unit": payload.weight_unit,
        "weight": payload.weight,
    }
    if payload.description is not None:
        item_payload["description"] = payload.description

    task_id: int | None = None
    import_status: str | None = None
    created_product_id: int | None = None
    errors: list[dict] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            import_response = client.post(
                "https://api-seller.ozon.ru/v3/product/import",
                headers=headers,
                json={"items": [item_payload]},
            )
            if import_response.status_code != 200:
                message = "Не удалось создать позицию в Ozon."
                try:
                    message = str((import_response.json() or {}).get("message") or message)
                except ValueError:
                    if import_response.text:
                        message = import_response.text[:300]
                raise HTTPException(status_code=422, detail=message)

            import_payload = import_response.json() if import_response.headers.get("content-type", "").startswith("application/json") else {}
            task_id = int((import_payload.get("result") or {}).get("task_id") or 0) or None

            if task_id:
                for _ in range(8):
                    time.sleep(1.2)
                    info_response = client.post(
                        "https://api-seller.ozon.ru/v1/product/import/info",
                        headers=headers,
                        json={"task_id": task_id},
                    )
                    if info_response.status_code != 200:
                        continue
                    info_payload = info_response.json() if info_response.headers.get("content-type", "").startswith("application/json") else {}
                    items = ((info_payload.get("result") or {}).get("items") or [])
                    if not items or not isinstance(items, list):
                        continue
                    first_item = items[0] if isinstance(items[0], dict) else {}
                    import_status = first_item.get("status")
                    try:
                        created_product_id = int(first_item.get("product_id") or 0) or None
                    except (TypeError, ValueError):
                        created_product_id = None
                    raw_errors = first_item.get("errors")
                    if isinstance(raw_errors, list):
                        errors = [err for err in raw_errors if isinstance(err, dict)]
                    if import_status in {"imported", "failed"}:
                        break

            price_value = (payload.price or "").strip()
            if price_value:
                prices_payload: dict = {
                    "prices": [
                        {
                            "offer_id": payload.offer_id.strip(),
                            "price": price_value,
                            "currency_code": payload.currency_code.strip().upper() or "RUB",
                        }
                    ]
                }
                if payload.old_price and payload.old_price.strip():
                    prices_payload["prices"][0]["old_price"] = payload.old_price.strip()
                _ = client.post(
                    "https://api-seller.ozon.ru/v1/product/import/prices",
                    headers=headers,
                    json=prices_payload,
                )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с Ozon: {exc.__class__.__name__}") from exc

    add_audit(
        db,
        "product.created.ozon",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product",
        resource_id=payload.offer_id.strip(),
        metadata={
            "offer_id": payload.offer_id.strip(),
            "task_id": task_id,
            "import_status": import_status,
            "product_id": created_product_id,
            "images_count": len(image_urls),
            "videos_count": len(video_urls),
            "errors_count": len(errors),
        },
    )
    db.commit()

    return OzonProductCreateOut(
        offer_id=payload.offer_id.strip(),
        task_id=task_id,
        import_status=import_status,
        product_id=created_product_id,
        message="Позиция отправлена в Ozon. Проверьте статус импорта.",
        errors=errors,
    )


@router.get("/{team_id}/connections/{connection_id}/ozon/attributes", response_model=list[OzonAttributeOut])
def get_ozon_category_attributes(
    team_id: int,
    connection_id: int,
    description_category_id: int = Query(..., ge=1),
    type_id: int = Query(..., ge=1),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[OzonAttributeOut]:
    _user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ozon_attributes",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if connection.provider != Marketplace.ozon.value:
        raise HTTPException(status_code=422, detail="Endpoint available only for Ozon")
    credential = get_active_connection_credential(db, connection_id)
    if credential is None or not credential.client_id_plain or not credential.api_key_plain:
        raise HTTPException(status_code=422, detail="Нет активного Ozon Seller ключа")

    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }
    body = {
        "description_category_id": description_category_id,
        "type_id": type_id,
        "language": "DEFAULT",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post("https://api-seller.ozon.ru/v1/description-category/attribute", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с Ozon: {exc.__class__.__name__}") from exc
    if response.status_code != 200:
        message = "Не удалось получить атрибуты категории Ozon"
        try:
            message = str((response.json() or {}).get("message") or message)
        except ValueError:
            if response.text:
                message = response.text[:300]
        raise HTTPException(status_code=422, detail=message)

    payload_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    rows = payload_json.get("result") if isinstance(payload_json, dict) else []
    if not isinstance(rows, list):
        return []
    result: list[OzonAttributeOut] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            OzonAttributeOut(
                id=int(row.get("id") or 0),
                attribute_complex_id=int(row.get("attribute_complex_id") or 0),
                name=str(row.get("name") or ""),
                description=(str(row.get("description")) if row.get("description") is not None else None),
                type=(str(row.get("type")) if row.get("type") is not None else None),
                is_collection=bool(row.get("is_collection")),
                is_required=bool(row.get("is_required")),
                max_value_count=int(row.get("max_value_count") or 0) if row.get("max_value_count") is not None else None,
                dictionary_id=int(row.get("dictionary_id") or 0) if row.get("dictionary_id") is not None else None,
                group_name=(str(row.get("group_name")) if row.get("group_name") is not None else None),
            )
        )
    return result


@router.get("/{team_id}/connections/{connection_id}/ozon/attributes/{attribute_id}/values", response_model=list[OzonAttributeValueOut])
def get_ozon_attribute_values(
    team_id: int,
    connection_id: int,
    attribute_id: int,
    description_category_id: int = Query(..., ge=1),
    type_id: int = Query(..., ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    last_value_id: int = Query(default=0, ge=0),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[OzonAttributeValueOut]:
    _user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ozon_attribute_values",
        resource_id=str(attribute_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if connection.provider != Marketplace.ozon.value:
        raise HTTPException(status_code=422, detail="Endpoint available only for Ozon")
    credential = get_active_connection_credential(db, connection_id)
    if credential is None or not credential.client_id_plain or not credential.api_key_plain:
        raise HTTPException(status_code=422, detail="Нет активного Ozon Seller ключа")

    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }
    body = {
        "attribute_id": attribute_id,
        "description_category_id": description_category_id,
        "type_id": type_id,
        "limit": limit,
        "last_value_id": last_value_id,
        "language": "DEFAULT",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post("https://api-seller.ozon.ru/v1/description-category/attribute/values", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с Ozon: {exc.__class__.__name__}") from exc
    if response.status_code != 200:
        message = "Не удалось получить значения атрибута Ozon"
        try:
            message = str((response.json() or {}).get("message") or message)
        except ValueError:
            if response.text:
                message = response.text[:300]
        raise HTTPException(status_code=422, detail=message)

    payload_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    rows = payload_json.get("result") if isinstance(payload_json, dict) else []
    if not isinstance(rows, list):
        return []
    result: list[OzonAttributeValueOut] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value_id_raw = row.get("id")
        try:
            value_id = int(value_id_raw or 0)
        except (TypeError, ValueError):
            value_id = 0
        result.append(
            OzonAttributeValueOut(
                id=value_id,
                value=str(row.get("value") or ""),
                info=(str(row.get("info")) if row.get("info") is not None else None),
                picture=(str(row.get("picture")) if row.get("picture") is not None else None),
            )
        )
    return result


@router.post("/{team_id}/connections/{connection_id}/products/ozon/content-rating", response_model=OzonContentRatingRefreshOut)
def refresh_ozon_content_rating(
    team_id: int,
    connection_id: int,
    payload: OzonContentRatingRefreshRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> OzonContentRatingRefreshOut:
    user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ozon_content_rating",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if connection.provider != Marketplace.ozon.value:
        raise HTTPException(status_code=422, detail="Endpoint available only for Ozon")
    credential = get_active_connection_credential(db, connection_id)
    if credential is None or not credential.client_id_plain or not credential.api_key_plain:
        raise HTTPException(status_code=422, detail="Нет активного Ozon Seller ключа")

    query = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.connection_id == connection_id)
        .filter(MarketplaceProduct.provider == connection.provider)
        .filter(MarketplaceProduct.is_current.is_(True))
        .order_by(MarketplaceProduct.updated_at.desc(), MarketplaceProduct.id.desc())
    )
    product_row_ids = [row_id for row_id in payload.product_row_ids if row_id > 0]
    if product_row_ids:
        query = query.filter(MarketplaceProduct.id.in_(product_row_ids))
    rows = query.limit(payload.limit).all()

    def normalize_sku_key(value: str) -> str:
        raw = value.strip()
        if not raw:
            return ""
        digits_only = "".join(ch for ch in raw if ch.isdigit())
        if digits_only:
            try:
                return str(int(digits_only))
            except ValueError:
                return digits_only.lstrip("0") or "0"
        return raw.lower()

    row_by_sku: dict[str, MarketplaceProduct] = {}
    for row in rows:
        payload_row = row.payload if isinstance(row.payload, dict) else {}
        info_item = payload_row.get("info_item") if isinstance(payload_row, dict) else {}
        info_item = info_item if isinstance(info_item, dict) else {}
        sku_candidates = [
            str(row.external_sku or "").strip(),
            str(info_item.get("sku") or "").strip(),
        ]
        sku_candidates = [candidate for candidate in sku_candidates if candidate]
        if not sku_candidates:
            continue
        if payload.only_missing:
            cached = (row.payload or {}).get("content_rating")
            if isinstance(cached, dict) and cached.get("rating") is not None:
                continue
        for sku_raw in sku_candidates:
            if sku_raw not in row_by_sku:
                row_by_sku[sku_raw] = row

    if not row_by_sku:
        return OzonContentRatingRefreshOut(
            updated_count=0,
            requested_skus=0,
            items=[],
            message="Нет товаров со SKU для расчета контент-рейтинга.",
        )

    def parse_float(value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def parse_int(value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }
    now = datetime.now(tz=timezone.utc)
    rating_by_sku: dict[str, dict] = {}
    rating_by_sku_norm: dict[str, dict] = {}
    sku_keys = list(row_by_sku.keys())
    sku_batches = [sku_keys[i : i + 200] for i in range(0, len(sku_keys), 200)]
    try:
        with httpx.Client(timeout=25.0) as client:
            for batch in sku_batches:
                sku_payload: list[int | str] = []
                for sku in batch:
                    if sku.isdigit():
                        try:
                            sku_payload.append(int(sku))
                        except ValueError:
                            sku_payload.append(sku)
                    else:
                        sku_payload.append(sku)
                response = client.post(
                    "https://api-seller.ozon.ru/v1/product/rating-by-sku",
                    headers=headers,
                    json={"skus": sku_payload},
                )
                if response.status_code != 200:
                    message = "Не удалось получить контент-рейтинг Ozon"
                    try:
                        message = str((response.json() or {}).get("message") or message)
                    except ValueError:
                        if response.text:
                            message = response.text[:300]
                    raise HTTPException(status_code=422, detail=message)
                payload_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                items = payload_json.get("products") if isinstance(payload_json, dict) else []
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    sku_value = str(item.get("sku") or "").strip()
                    if sku_value:
                        rating_by_sku[sku_value] = item
                        sku_norm = normalize_sku_key(sku_value)
                        if sku_norm:
                            rating_by_sku_norm[sku_norm] = item
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с Ozon: {exc.__class__.__name__}") from exc

    updated_count = 0
    result_items: list[OzonContentRatingItemOut] = []
    processed_row_ids: set[int] = set()
    for sku, row in row_by_sku.items():
        if row.id in processed_row_ids:
            continue
        source = rating_by_sku.get(sku)
        if not isinstance(source, dict):
            source = rating_by_sku_norm.get(normalize_sku_key(sku))
        if not isinstance(source, dict):
            continue
        groups_raw = source.get("groups") if isinstance(source.get("groups"), list) else []
        groups_out: list[OzonContentRatingGroupOut] = []
        groups_json: list[dict] = []
        for group_raw in groups_raw:
            if not isinstance(group_raw, dict):
                continue
            conditions = group_raw.get("conditions") if isinstance(group_raw.get("conditions"), list) else []
            missing_conditions_out: list[OzonContentRatingConditionOut] = []
            missing_conditions_json: list[dict] = []
            for condition_raw in conditions:
                if not isinstance(condition_raw, dict):
                    continue
                fulfilled = bool(condition_raw.get("fulfilled"))
                if fulfilled:
                    continue
                condition_out = OzonContentRatingConditionOut(
                    key=str(condition_raw.get("key") or "") or None,
                    description=str(condition_raw.get("description") or "") or None,
                    fulfilled=False,
                    cost=parse_float(condition_raw.get("cost")),
                )
                missing_conditions_out.append(condition_out)
                missing_conditions_json.append(condition_out.model_dump())

            improve_attributes_raw = group_raw.get("improve_attributes") if isinstance(group_raw.get("improve_attributes"), list) else []
            improve_attributes_out: list[OzonContentRatingImproveAttributeOut] = []
            improve_attributes_json: list[dict] = []
            for attr_raw in improve_attributes_raw:
                if not isinstance(attr_raw, dict):
                    continue
                attr_out = OzonContentRatingImproveAttributeOut(
                    id=parse_int(attr_raw.get("id")),
                    name=str(attr_raw.get("name") or "") or None,
                )
                improve_attributes_out.append(attr_out)
                improve_attributes_json.append(attr_out.model_dump())

            group_out = OzonContentRatingGroupOut(
                key=str(group_raw.get("key") or "") or None,
                name=str(group_raw.get("name") or "") or None,
                rating=parse_float(group_raw.get("rating")),
                weight=parse_float(group_raw.get("weight")),
                improve_at_least=parse_int(group_raw.get("improve_at_least")),
                missing_conditions=missing_conditions_out,
                improve_attributes=improve_attributes_out,
            )
            groups_out.append(group_out)
            groups_json.append(
                {
                    "key": group_out.key,
                    "name": group_out.name,
                    "rating": group_out.rating,
                    "weight": group_out.weight,
                    "improve_at_least": group_out.improve_at_least,
                    "missing_conditions": missing_conditions_json,
                    "improve_attributes": improve_attributes_json,
                }
            )

        rating_value = parse_float(source.get("rating"))
        payload_data = dict(row.payload or {})
        payload_data["content_rating"] = {
            "sku": sku,
            "rating": rating_value,
            "groups": groups_json,
            "fetched_at": now.isoformat(),
        }
        row.payload = payload_data
        row.updated_at = now
        updated_count += 1
        processed_row_ids.add(row.id)
        result_items.append(
            OzonContentRatingItemOut(
                product_row_id=row.id,
                sku=sku,
                offer_id=row.external_offer_id,
                rating=rating_value,
                groups=groups_out,
                fetched_at=now,
            )
        )

    add_audit(
        db,
        action="ozon.content_rating.refresh",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ozon_content_rating",
        resource_id=str(connection_id),
        metadata={
            "connection_id": connection_id,
            "requested_skus": len(sku_keys),
            "updated_count": updated_count,
        },
    )
    db.commit()

    return OzonContentRatingRefreshOut(
        updated_count=updated_count,
        requested_skus=len(sku_keys),
        items=result_items,
        message=f"Контент-рейтинг обновлен для {updated_count} товаров.",
    )


@router.post("/{team_id}/connections/{connection_id}/products/{product_row_id}/ai/card-draft", response_model=AiCardDraftOut)
def create_ai_product_card_draft(
    team_id: int,
    connection_id: int,
    product_row_id: int,
    payload: AiCardDraftRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> AiCardDraftOut:
    user, _session = user_with_session
    require_team_permission(Permission.AGENT_CHAT, member)
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ai_product_card_draft",
        resource_id=str(product_row_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    row = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.id == product_row_id)
        .filter(MarketplaceProduct.connection_id == connection_id)
        .filter(MarketplaceProduct.provider == connection.provider)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        draft, usage, log_id = generate_ai_card_draft(
            db,
            row=row,
            user_id=user.id,
            team_id=team_id,
            connection_id=connection_id,
            current_fields=payload.current_fields,
            image_urls=payload.image_urls,
            user_prompt=(payload.user_prompt or "").strip(),
            template_id=payload.template_id,
            reference=payload.reference,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка связи с AI provider: {exc.__class__.__name__}") from exc

    warnings = draft.get("warnings") if isinstance(draft.get("warnings"), list) else []
    add_audit(
        db,
        "ai.product_card.draft",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product",
        resource_id=str(product_row_id),
        metadata={
            "log_id": log_id,
            "provider": "openai",
            "template_id": payload.template_id,
            "total_tokens": usage.get("total_tokens", 0),
        },
    )
    db.commit()

    return AiCardDraftOut(
        draft_id=log_id,
        log_id=log_id,
        status="ready",
        model=usage.get("model", "") or "gpt-5.1",
        photo_analysis=draft.get("photo_analysis") if isinstance(draft.get("photo_analysis"), dict) else {},
        field_checks=draft.get("field_checks") if isinstance(draft.get("field_checks"), list) else [],
        field_recommendations=draft.get("field_recommendations") if isinstance(draft.get("field_recommendations"), list) else [],
        media_recommendations=draft.get("media_recommendations") if isinstance(draft.get("media_recommendations"), list) else [],
        draft=draft.get("draft") if isinstance(draft.get("draft"), dict) else {},
        prompt_analysis=draft.get("prompt_analysis") if isinstance(draft.get("prompt_analysis"), dict) else {},
        reference_analysis=draft.get("reference_analysis") if isinstance(draft.get("reference_analysis"), dict) else {},
        template_plan=draft.get("template_plan") if isinstance(draft.get("template_plan"), dict) else {},
        warnings=[str(item) for item in warnings],
        usage=usage,
    )


@router.post("/{team_id}/connections/{connection_id}/products/{product_row_id}/ai/media-image", response_model=AiMediaGenerateOut)
def create_ai_product_media_image(
    team_id: int,
    connection_id: int,
    product_row_id: int,
    payload: AiMediaGenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> AiMediaGenerateOut:
    user, _session = user_with_session
    require_team_permission(Permission.AGENT_CHAT, member)
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ai_product_media_image",
        resource_id=str(product_row_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    row = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.id == product_row_id)
        .filter(MarketplaceProduct.connection_id == connection_id)
        .filter(MarketplaceProduct.provider == connection.provider)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        log_row = create_ai_media_image_job(
            db,
            row=row,
            user_id=user.id,
            team_id=team_id,
            connection_id=connection_id,
            source_image_url=payload.source_image_url,
            user_prompt=payload.prompt,
            reference=payload.reference,
            output_format=payload.output_format,
            size=payload.size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(run_ai_media_image_job, log_row.id)

    add_audit(
        db,
        "ai.product_media.image_queued",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_product",
        resource_id=str(product_row_id),
        metadata={
            "log_id": log_row.id,
            "provider": "openai",
            "model": log_row.model_image,
        },
    )
    db.commit()

    return AiMediaGenerateOut(
        log_id=log_row.id,
        status=log_row.status,
        model=log_row.model_image or "gpt-image-1.5",
        progress=5,
        message="AI image generation queued",
        usage={},
    )


def _ai_media_progress(row) -> int:
    if row.status == AiGenerationStatus.success.value:
        return 100
    if row.status == AiGenerationStatus.failed.value:
        return 100
    if row.status == AiGenerationStatus.queued.value:
        return 5
    created_at = row.created_at if row.created_at.tzinfo is not None else row.created_at.replace(tzinfo=timezone.utc)
    elapsed_ms = max(0, int((datetime.now(tz=timezone.utc) - created_at).total_seconds() * 1000))
    return min(95, 10 + int(elapsed_ms / 600))


@router.get("/{team_id}/connections/{connection_id}/products/{product_row_id}/ai/media-image/{log_id}", response_model=AiMediaGenerateOut)
def get_ai_product_media_image_status(
    team_id: int,
    connection_id: int,
    product_row_id: int,
    log_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> AiMediaGenerateOut:
    _user, _session = user_with_session
    require_team_permission(Permission.AGENT_CHAT, member)
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="ai_product_media_image",
        resource_id=str(product_row_id),
    )
    log_row = db.query(AiGenerationLog).filter(AiGenerationLog.id == log_id).first()
    if (
        log_row is None
        or log_row.team_id != team_id
        or log_row.connection_id != connection_id
        or log_row.product_row_id != product_row_id
        or log_row.operation != "media_image_edit"
    ):
        raise HTTPException(status_code=404, detail="AI media job not found")

    response_payload = log_row.response if isinstance(log_row.response, dict) else {}
    usage = {
        "prompt_tokens": log_row.prompt_tokens,
        "completion_tokens": log_row.completion_tokens,
        "total_tokens": log_row.total_tokens,
        "cached_input_tokens": log_row.cached_input_tokens,
        "reasoning_tokens": log_row.reasoning_tokens,
    }
    image_url = response_payload.get("image_url") if isinstance(response_payload.get("image_url"), str) else None
    revised_prompt = response_payload.get("revised_prompt") if isinstance(response_payload.get("revised_prompt"), str) else None
    return AiMediaGenerateOut(
        log_id=log_row.id,
        status=log_row.status,
        model=log_row.model_image or "gpt-image-1.5",
        image_url=image_url,
        revised_prompt=revised_prompt,
        progress=_ai_media_progress(log_row),
        message="AI image is ready" if log_row.status == AiGenerationStatus.success.value else "AI image generation is in progress",
        error_message=log_row.error_message,
        usage=usage,
    )


@router.get("/{team_id}/analytics/products/export.csv")
def export_analytics_products_csv(
    team_id: int,
    connection_id: int = Query(..., ge=1),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> Response:
    _user, _session = user_with_session
    access = enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.ANALYTICS_EXPORT,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="analytics_products_export",
        resource_id=str(connection_id),
    )

    query = (
        db.query(AnalyticsProductFact)
        .filter(AnalyticsProductFact.team_id == team_id)
        .filter(AnalyticsProductFact.connection_id == connection_id)
        .order_by(AnalyticsProductFact.id.asc())
    )
    if access is not None and access.access_mode == ConnectionAccessMode.scoped.value:
        scopes = build_scope_filter(member, connection_id, db)
        if not scopes:
            rows: list[AnalyticsProductFact] = []
        else:
            rows = apply_product_scopes(query, scopes).all()
    else:
        rows = query.all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "sku", "brand", "category", "warehouse", "orders_count", "revenue_amount"])
    for row in rows:
        writer.writerow([row.id, row.sku, row.brand, row.category, row.warehouse or "", row.orders_count, row.revenue_amount])
    payload = buffer.getvalue()
    headers = {"Content-Disposition": f'attachment; filename="products-team-{team_id}-connection-{connection_id}.csv"'}
    return Response(content=payload, media_type="text/csv", headers=headers)


@router.get("/{team_id}/dashboard", response_model=DashboardOut)
def get_team_dashboard(
    team_id: int,
    connection_id: int | None = Query(default=None, ge=1),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> DashboardOut:
    _user, _session = user_with_session
    selected_connection: MarketplaceConnection | None = None
    access: ConnectionAccess | None = None

    if connection_id is not None:
        selected_connection = get_team_connection_or_404(db, team_id, connection_id)
        access = enforce_connection_permission(
            db=db,
            request=request,
            member=member,
            permission=Permission.ANALYTICS_READ,
            team_id=team_id,
            connection_id=connection_id,
            resource_type="dashboard",
            resource_id=str(connection_id),
        )
        query = (
            db.query(AnalyticsProductFact)
            .filter(AnalyticsProductFact.team_id == team_id)
            .filter(AnalyticsProductFact.connection_id == connection_id)
        )
        if access is not None and access.access_mode == ConnectionAccessMode.scoped.value:
            scopes = build_scope_filter(member, connection_id, db)
            if not scopes:
                products_total = 0
                orders_total = 0
                revenue_total = 0
            else:
                scoped_query = apply_product_scopes(query, scopes)
                stats = scoped_query.with_entities(
                    func.count(AnalyticsProductFact.id),
                    func.coalesce(func.sum(AnalyticsProductFact.orders_count), 0),
                    func.coalesce(func.sum(AnalyticsProductFact.revenue_amount), 0),
                ).one()
                products_total, orders_total, revenue_total = int(stats[0] or 0), int(stats[1] or 0), int(stats[2] or 0)
        else:
            stats = query.with_entities(
                func.count(AnalyticsProductFact.id),
                func.coalesce(func.sum(AnalyticsProductFact.orders_count), 0),
                func.coalesce(func.sum(AnalyticsProductFact.revenue_amount), 0),
            ).one()
            products_total, orders_total, revenue_total = int(stats[0] or 0), int(stats[1] or 0), int(stats[2] or 0)
    else:
        products_total = 0
        orders_total = 0
        revenue_total = 0

    recommendations = select_dashboard_recommendations(
        db,
        team_role=member.role,
        connection_provider=selected_connection.provider if selected_connection else None,
    )
    return DashboardOut(
        team_id=team_id,
        connection_id=connection_id,
        products_total=products_total,
        orders_total=orders_total,
        revenue_total=revenue_total,
        recommendations=[DashboardRecommendationOut.model_validate(item) for item in recommendations],
    )


@router.get("/{team_id}/sync-jobs", response_model=list[SyncJobOut])
def get_sync_jobs(
    team_id: int,
    connection_id: int = Query(..., ge=1),
    request: Request = None,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[SyncJobOut]:
    _user, _session = user_with_session
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.SYNC_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="sync_job",
        resource_id=str(connection_id),
    )
    return (
        db.query(SyncJob)
        .filter(SyncJob.team_id == team_id)
        .filter(SyncJob.connection_id == connection_id)
        .order_by(SyncJob.id.desc())
        .limit(100)
        .all()
    )


@router.post("/{team_id}/connections/{connection_id}/sync/run", response_model=SyncJobOut)
def run_connection_sync(
    team_id: int,
    connection_id: int,
    payload: SyncRunRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> SyncJobOut:
    user, _session = user_with_session
    connection = get_team_connection_or_404(db, team_id, connection_id)
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.SYNC_RUN,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="sync_job",
        resource_id=str(connection_id),
    )
    now = datetime.now(tz=timezone.utc)
    job = SyncJob(
        team_id=team_id,
        connection_id=connection_id,
        provider=connection.provider,
        status=SyncJobStatus.running.value,
        domain=SyncDomain.products.value,
        stage=payload.stage or "READY",
        dry_run=payload.dry_run,
        processed_rows=0,
        requested_by_user_id=user.id,
        started_at=now,
    )
    db.add(job)
    db.flush()
    add_audit(
        db,
        "sync.run.requested",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="sync_job",
        resource_id=str(job.id),
        metadata={"dry_run": payload.dry_run, "stage": job.stage},
    )
    status, processed_rows, error_message = sync_products_for_connection(
        db,
        connection=connection,
        requested_by_user_id=user.id,
        dry_run=payload.dry_run,
        sync_job_id=job.id,
    )
    job.status = status
    job.processed_rows = processed_rows
    job.error_message = error_message
    job.finished_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{team_id}/connections/{connection_id}/costs/import", response_model=CostImportOut)
def import_connection_costs(
    team_id: int,
    connection_id: int,
    payload: CostImportRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> CostImportOut:
    user, _session = user_with_session
    get_team_connection_or_404(db, team_id, connection_id)
    enforce_connection_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.COSTS_IMPORT,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="cost_import",
        resource_id=str(connection_id),
    )
    if payload.accepted_rows + payload.rejected_rows > payload.total_rows:
        raise HTTPException(status_code=422, detail="Invalid rows counters")

    row = CostImport(
        team_id=team_id,
        connection_id=connection_id,
        file_name=payload.file_name.strip(),
        total_rows=payload.total_rows,
        accepted_rows=payload.accepted_rows,
        rejected_rows=payload.rejected_rows,
        imported_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        "costs.imported",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="cost_import",
        resource_id=str(row.id),
        metadata={"file_name": row.file_name, "total_rows": row.total_rows, "accepted_rows": row.accepted_rows, "rejected_rows": row.rejected_rows},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/{team_id}/connections", response_model=list[MarketplaceConnectionOut])
def list_team_connections(
    team_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[MarketplaceConnectionOut]:
    _user, _session = user_with_session
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.CONNECTIONS_READ, team_id=team_id, resource_type="team", resource_id=str(team_id))
    rows = (
        db.query(MarketplaceConnection)
        .filter(MarketplaceConnection.team_id == team_id)
        .order_by(MarketplaceConnection.id.asc())
        .all()
    )
    return rows


@router.post("/{team_id}/connections/validate/ozon-seller", response_model=MarketplaceKeyValidationOut)
def validate_ozon_seller_key(
    team_id: int,
    payload: OzonSellerKeyValidationRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceKeyValidationOut:
    _user, _session = user_with_session
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_CREATE,
        team_id=team_id,
        resource_type="marketplace_connection_credential_validation",
        resource_id="ozon-seller",
    )

    checked_at = datetime.now(tz=timezone.utc)
    try:
        response = httpx.post(
            "https://api-seller.ozon.ru/v4/product/info/limit",
            headers={
                "Client-Id": payload.client_id.strip(),
                "Api-Key": payload.api_key.strip(),
                "Content-Type": "application/json",
            },
            json={},
            timeout=8.0,
        )
    except httpx.TimeoutException:
        return MarketplaceKeyValidationOut(
            is_valid=False,
            status_code=None,
            message="Ozon не ответил за 8 секунд. Проверьте интернет или попробуйте позже.",
            checked_at=checked_at,
        )
    except httpx.HTTPError as exc:
        return MarketplaceKeyValidationOut(
            is_valid=False,
            status_code=None,
            message=f"Не удалось подключиться к Ozon Seller API: {exc.__class__.__name__}",
            checked_at=checked_at,
        )

    if response.status_code == 200:
        payload_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        details = payload_json if isinstance(payload_json, dict) else {}
        return MarketplaceKeyValidationOut(
            is_valid=True,
            status_code=response.status_code,
            message="Ключ Seller API валиден.",
            checked_at=checked_at,
            details={
                "daily_create_limit": details.get("daily_create", {}).get("limit") if isinstance(details.get("daily_create"), dict) else None,
                "daily_update_limit": details.get("daily_update", {}).get("limit") if isinstance(details.get("daily_update"), dict) else None,
                "total_limit": details.get("total", {}).get("limit") if isinstance(details.get("total"), dict) else None,
            },
        )

    message = "Ключ Seller API не прошел проверку."
    try:
        error_payload = response.json()
        if isinstance(error_payload, dict):
            message = str(error_payload.get("message") or error_payload.get("error") or message)
    except ValueError:
        if response.text:
            message = response.text[:300]

    if response.status_code in {401, 403}:
        message = "Ozon отклонил Client ID или ключ доступа. Проверьте значения и права ключа."
    elif "obsolete method" in message.lower():
        message = "Ozon вернул ошибку устаревшего метода. Проверка настроена на старый endpoint, обновите приложение."

    return MarketplaceKeyValidationOut(
        is_valid=False,
        status_code=response.status_code,
        message=message,
        checked_at=checked_at,
    )


@router.post("/{team_id}/connections/validate/ozon-performance", response_model=MarketplaceKeyValidationOut)
def validate_ozon_performance_key(
    team_id: int,
    payload: OzonPerformanceKeyValidationRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceKeyValidationOut:
    _user, _session = user_with_session
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_CREATE,
        team_id=team_id,
        resource_type="marketplace_connection_credential_validation",
        resource_id="ozon-performance",
    )

    checked_at = datetime.now(tz=timezone.utc)
    try:
        response = httpx.post(
            "https://api-performance.ozon.ru/api/client/token",
            json={
                "client_id": payload.client_id.strip(),
                "client_secret": payload.client_secret.strip(),
                "grant_type": "client_credentials",
            },
            timeout=8.0,
        )
    except httpx.TimeoutException:
        return MarketplaceKeyValidationOut(
            is_valid=False,
            status_code=None,
            message="Ozon Performance API не ответил за 8 секунд. Попробуйте позже.",
            checked_at=checked_at,
        )
    except httpx.HTTPError as exc:
        return MarketplaceKeyValidationOut(
            is_valid=False,
            status_code=None,
            message=f"Не удалось подключиться к Ozon Performance API: {exc.__class__.__name__}",
            checked_at=checked_at,
        )

    try:
        payload_json = response.json()
    except ValueError:
        payload_json = {}

    if response.status_code == 200 and isinstance(payload_json, dict) and payload_json.get("access_token"):
        return MarketplaceKeyValidationOut(
            is_valid=True,
            status_code=response.status_code,
            message="Ключ Performance API валиден.",
            checked_at=checked_at,
            details={
                "token_type": payload_json.get("token_type"),
                "expires_in": payload_json.get("expires_in"),
            },
        )

    message = "Ключ Performance API не прошел проверку."
    if isinstance(payload_json, dict):
        message = str(payload_json.get("error_description") or payload_json.get("message") or payload_json.get("error") or message)
    elif response.text:
        message = response.text[:300]

    if response.status_code in {400, 401, 403}:
        message = "Ozon отклонил Client ID или Client Secret Performance API. Проверьте значения сервисного аккаунта."

    return MarketplaceKeyValidationOut(
        is_valid=False,
        status_code=response.status_code,
        message=message,
        checked_at=checked_at,
    )


@router.post("/{team_id}/connections", response_model=MarketplaceConnectionOut)
def create_team_connection(
    team_id: int,
    payload: MarketplaceConnectionCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceConnectionOut:
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.CONNECTIONS_CREATE, team_id=team_id, resource_type="marketplace_connection")
    user, _ = user_with_session
    row = MarketplaceConnection(
        team_id=team_id,
        provider=parse_marketplace(payload.provider),
        name=payload.name.strip(),
        status=ConnectionStatus.active.value,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        is_disabled=False,
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        "connection.created",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=row.id,
        resource_type="marketplace_connection",
        resource_id=str(row.id),
        metadata={"provider": row.provider, "name": row.name},
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{team_id}/connections/{connection_id}", response_model=MarketplaceConnectionOut)
def patch_team_connection(
    team_id: int,
    connection_id: int,
    payload: MarketplaceConnectionPatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceConnectionOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    if payload.name is not None:
        connection.name = payload.name.strip()
    if payload.status is not None:
        connection.status = parse_connection_status(payload.status)
    if payload.is_disabled is not None:
        connection.is_disabled = payload.is_disabled

    user, _ = user_with_session
    connection.updated_by_user_id = user.id
    add_audit(
        db,
        "connection.updated",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection",
        resource_id=str(connection_id),
        metadata={"name": connection.name, "status": connection.status, "is_disabled": connection.is_disabled},
    )
    db.commit()
    db.refresh(connection)
    return connection


@router.delete("/{team_id}/connections/{connection_id}", response_model=MessageOut)
def delete_team_connection(
    team_id: int,
    connection_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MessageOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_DELETE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    connection.is_disabled = True
    connection.status = ConnectionStatus.disabled.value
    user, _ = user_with_session
    connection.updated_by_user_id = user.id
    add_audit(
        db,
        "connection.deleted",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection",
        resource_id=str(connection_id),
    )
    db.commit()
    return MessageOut(message="Connection disabled")


@router.get("/{team_id}/connections/{connection_id}/credentials", response_model=list[MarketplaceCredentialOut])
def list_connection_credentials(
    team_id: int,
    connection_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[MarketplaceConnectionCredential]:
    _user, _session = user_with_session
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(connection_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    return (
        db.query(MarketplaceConnectionCredential)
        .filter(MarketplaceConnectionCredential.connection_id == connection_id)
        .order_by(MarketplaceConnectionCredential.is_active.desc(), MarketplaceConnectionCredential.id.asc())
        .all()
    )


@router.post("/{team_id}/connections/{connection_id}/credentials", response_model=MarketplaceCredentialOut)
def create_connection_credential(
    team_id: int,
    connection_id: int,
    payload: MarketplaceCredentialCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceConnectionCredential:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(connection_id),
    )
    connection = get_team_connection_or_404(db, team_id, connection_id)
    user, _ = user_with_session
    credential = MarketplaceConnectionCredential(
        connection_id=connection.id,
        provider=connection.provider,
        credential_kind=normalize_credential_kind(payload.credential_kind),
        auth_scheme=parse_credential_auth_scheme(payload.auth_scheme),
        name=payload.name.strip(),
        client_id_plain=payload.client_id_plain,
        api_key_plain=payload.api_key_plain,
        client_secret_plain=payload.client_secret_plain,
        access_token_plain=payload.access_token_plain,
        refresh_token_plain=payload.refresh_token_plain,
        scopes=payload.scopes_json,
        token_meta=payload.token_meta_json,
        expires_at=payload.expires_at,
        is_primary=payload.is_primary,
        is_active=payload.is_active,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(credential)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Credential with this kind and name already exists") from exc

    add_audit(
        db,
        "connection.credential.created",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(credential.id),
        metadata={
            "credential_kind": credential.credential_kind,
            "auth_scheme": credential.auth_scheme,
            "name": credential.name,
            "is_primary": credential.is_primary,
            "is_active": credential.is_active,
        },
    )
    db.commit()
    db.refresh(credential)
    return credential


@router.patch("/{team_id}/connections/{connection_id}/credentials/{credential_id}", response_model=MarketplaceCredentialOut)
def patch_connection_credential(
    team_id: int,
    connection_id: int,
    credential_id: int,
    payload: MarketplaceCredentialPatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MarketplaceConnectionCredential:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_UPDATE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(credential_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    credential = (
        db.query(MarketplaceConnectionCredential)
        .filter(MarketplaceConnectionCredential.id == credential_id)
        .filter(MarketplaceConnectionCredential.connection_id == connection_id)
        .first()
    )
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")

    if payload.credential_kind is not None:
        credential.credential_kind = normalize_credential_kind(payload.credential_kind)
    if payload.auth_scheme is not None:
        credential.auth_scheme = parse_credential_auth_scheme(payload.auth_scheme)
    if payload.name is not None:
        credential.name = payload.name.strip()
    for field_name in ("client_id_plain", "api_key_plain", "client_secret_plain", "access_token_plain", "refresh_token_plain"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(credential, field_name, value)
    if payload.scopes_json is not None:
        credential.scopes = payload.scopes_json
    if payload.token_meta_json is not None:
        credential.token_meta = payload.token_meta_json
    if payload.expires_at is not None:
        credential.expires_at = payload.expires_at
    if payload.is_primary is not None:
        credential.is_primary = payload.is_primary
    if payload.is_active is not None:
        credential.is_active = payload.is_active

    user, _ = user_with_session
    credential.updated_by_user_id = user.id
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Credential with this kind and name already exists") from exc

    add_audit(
        db,
        "connection.credential.updated",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(credential.id),
        metadata={
            "credential_kind": credential.credential_kind,
            "auth_scheme": credential.auth_scheme,
            "name": credential.name,
            "is_primary": credential.is_primary,
            "is_active": credential.is_active,
        },
    )
    db.commit()
    db.refresh(credential)
    return credential


@router.delete("/{team_id}/connections/{connection_id}/credentials/{credential_id}", response_model=MessageOut)
def delete_connection_credential(
    team_id: int,
    connection_id: int,
    credential_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MessageOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_DELETE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(credential_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    credential = (
        db.query(MarketplaceConnectionCredential)
        .filter(MarketplaceConnectionCredential.id == credential_id)
        .filter(MarketplaceConnectionCredential.connection_id == connection_id)
        .first()
    )
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")

    user, _ = user_with_session
    credential.is_active = False
    credential.updated_by_user_id = user.id
    add_audit(
        db,
        "connection.credential.disabled",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="marketplace_connection_credential",
        resource_id=str(credential.id),
        metadata={
            "credential_kind": credential.credential_kind,
            "auth_scheme": credential.auth_scheme,
            "name": credential.name,
            "is_primary": credential.is_primary,
            "is_active": credential.is_active,
        },
    )
    db.commit()
    return MessageOut(message="Credential disabled")


@router.get("/{team_id}/connections/{connection_id}/access", response_model=list[ConnectionAccessOut])
def list_connection_access(
    team_id: int,
    connection_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[ConnectionAccessOut]:
    _user, _session = user_with_session
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(connection_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    rows = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .order_by(ConnectionAccess.id.asc())
        .all()
    )
    return rows


@router.post("/{team_id}/connections/{connection_id}/access", response_model=ConnectionAccessOut)
def create_connection_access(
    team_id: int,
    connection_id: int,
    payload: ConnectionAccessCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> ConnectionAccessOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(connection_id),
        target_user_id=payload.team_member_id,
    )
    get_team_connection_or_404(db, team_id, connection_id)
    target_member = (
        db.query(TeamMember)
        .filter(TeamMember.id == payload.team_member_id)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.status == TeamMemberStatus.active.value)
        .first()
    )
    if target_member is None:
        raise HTTPException(status_code=404, detail="Team member not found")

    existing = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.connection_id == connection_id)
        .filter(ConnectionAccess.team_member_id == payload.team_member_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Access already exists")

    user, _ = user_with_session
    row = ConnectionAccess(
        team_id=team_id,
        connection_id=connection_id,
        team_member_id=payload.team_member_id,
        access_mode=parse_access_mode(payload.access_mode),
        is_active=payload.is_active,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        "connection.access.granted",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(row.id),
        metadata={"team_member_id": payload.team_member_id, "access_mode": row.access_mode, "is_active": row.is_active},
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{team_id}/connections/{connection_id}/access/{access_id}", response_model=ConnectionAccessOut)
def patch_connection_access(
    team_id: int,
    connection_id: int,
    access_id: int,
    payload: ConnectionAccessPatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> ConnectionAccessOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(access_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    row = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Connection access not found")

    if payload.access_mode is not None:
        row.access_mode = parse_access_mode(payload.access_mode)
    if payload.is_active is not None:
        row.is_active = payload.is_active

    user, _ = user_with_session
    row.updated_by_user_id = user.id
    add_audit(
        db,
        "connection.access.updated",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(row.id),
        metadata={"access_mode": row.access_mode, "is_active": row.is_active},
    )
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{team_id}/connections/{connection_id}/access/{access_id}", response_model=MessageOut)
def delete_connection_access(
    team_id: int,
    connection_id: int,
    access_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MessageOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(access_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    row = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Connection access not found")

    user, _ = user_with_session
    add_audit(
        db,
        "connection.access.revoked",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="connection_access",
        resource_id=str(row.id),
    )
    db.delete(row)
    db.commit()
    return MessageOut(message="Connection access removed")


@router.post("/{team_id}/connections/{connection_id}/access/{access_id}/scopes", response_model=AccessScopeOut)
def create_access_scope(
    team_id: int,
    connection_id: int,
    access_id: int,
    payload: AccessScopeCreateRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> AccessScopeOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(access_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    access = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Connection access not found")

    subject_type = parse_scope_subject_type(payload.subject_type)
    subject_value = payload.subject_value.strip()
    existing = (
        db.query(AccessScope)
        .filter(AccessScope.connection_access_id == access_id)
        .filter(AccessScope.subject_type == subject_type)
        .filter(AccessScope.subject_value == subject_value)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Scope already exists")

    user, _ = user_with_session
    scope = AccessScope(
        team_id=team_id,
        connection_access_id=access_id,
        subject_type=subject_type,
        subject_value=subject_value,
        is_excluded=payload.is_excluded,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(scope)
    db.flush()
    add_audit(
        db,
        "scope.created",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(scope.id),
        metadata={"access_id": access_id, "subject_type": subject_type, "subject_value": subject_value, "is_excluded": scope.is_excluded},
    )
    db.commit()
    db.refresh(scope)
    return scope


@router.get("/{team_id}/connections/{connection_id}/access/{access_id}/scopes", response_model=list[AccessScopeOut])
def list_access_scopes(
    team_id: int,
    connection_id: int,
    access_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[AccessScopeOut]:
    _user, _session = user_with_session
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_READ,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(access_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    access = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Connection access not found")
    return (
        db.query(AccessScope)
        .filter(AccessScope.team_id == team_id)
        .filter(AccessScope.connection_access_id == access_id)
        .order_by(AccessScope.id.asc())
        .all()
    )


@router.patch("/{team_id}/connections/{connection_id}/access/{access_id}/scopes/{scope_id}", response_model=AccessScopeOut)
def patch_access_scope(
    team_id: int,
    connection_id: int,
    access_id: int,
    scope_id: int,
    payload: AccessScopePatchRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> AccessScopeOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(scope_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    access = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Connection access not found")

    scope = (
        db.query(AccessScope)
        .filter(AccessScope.id == scope_id)
        .filter(AccessScope.team_id == team_id)
        .filter(AccessScope.connection_access_id == access_id)
        .first()
    )
    if scope is None:
        raise HTTPException(status_code=404, detail="Scope not found")

    next_subject_type = scope.subject_type
    next_subject_value = scope.subject_value
    if payload.subject_type is not None:
        next_subject_type = parse_scope_subject_type(payload.subject_type)
    if payload.subject_value is not None:
        next_subject_value = payload.subject_value.strip()
    if payload.subject_type is not None or payload.subject_value is not None:
        duplicate = (
            db.query(AccessScope)
            .filter(AccessScope.connection_access_id == access_id)
            .filter(AccessScope.subject_type == next_subject_type)
            .filter(AccessScope.subject_value == next_subject_value)
            .filter(AccessScope.id != scope_id)
            .first()
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Scope already exists")
        scope.subject_type = next_subject_type
        scope.subject_value = next_subject_value
    if payload.is_excluded is not None:
        scope.is_excluded = payload.is_excluded

    user, _ = user_with_session
    scope.updated_by_user_id = user.id
    add_audit(
        db,
        "scope.updated",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(scope.id),
        metadata={"access_id": access_id, "subject_type": scope.subject_type, "subject_value": scope.subject_value, "is_excluded": scope.is_excluded},
    )
    db.commit()
    db.refresh(scope)
    return scope


@router.delete("/{team_id}/connections/{connection_id}/access/{access_id}/scopes/{scope_id}", response_model=MessageOut)
def delete_access_scope(
    team_id: int,
    connection_id: int,
    access_id: int,
    scope_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> MessageOut:
    enforce_team_permission(
        db=db,
        request=request,
        member=member,
        permission=Permission.CONNECTIONS_SHARE,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(scope_id),
    )
    get_team_connection_or_404(db, team_id, connection_id)
    access = (
        db.query(ConnectionAccess)
        .filter(ConnectionAccess.id == access_id)
        .filter(ConnectionAccess.team_id == team_id)
        .filter(ConnectionAccess.connection_id == connection_id)
        .first()
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Connection access not found")
    scope = (
        db.query(AccessScope)
        .filter(AccessScope.id == scope_id)
        .filter(AccessScope.team_id == team_id)
        .filter(AccessScope.connection_access_id == access_id)
        .first()
    )
    if scope is None:
        raise HTTPException(status_code=404, detail="Scope not found")

    user, _ = user_with_session
    add_audit(
        db,
        "scope.deleted",
        user.id,
        request.client.host if request.client else None,
        team_id=team_id,
        connection_id=connection_id,
        resource_type="access_scope",
        resource_id=str(scope.id),
        metadata={"access_id": access_id},
    )
    db.delete(scope)
    db.commit()
    return MessageOut(message="Scope removed")


@router.get("/{team_id}/audit", response_model=list[AuditEventOut])
def get_team_audit(
    team_id: int,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    member: TeamMember = Depends(get_current_team_member),
    db: Session = Depends(get_db),
) -> list[AuditEventOut]:
    _user, _session = user_with_session
    enforce_team_permission(db=db, request=request, member=member, permission=Permission.AUDIT_READ, team_id=team_id, resource_type="audit", resource_id=str(team_id))
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.team_id == team_id)
        .order_by(AuditEvent.id.desc())
        .limit(100)
        .all()
    )
    return rows
