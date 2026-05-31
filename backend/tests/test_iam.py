from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalyticsProductFact,
    AuditEvent,
    DashboardRecommendation,
    MarketplaceConnection,
    MessengerAccountLink,
    PlatformRole,
    PlatformRoleAssignment,
    Team,
    TeamMember,
    TeamMemberStatus,
    TeamRole,
)


def register_and_login(client, *, email: str, phone: str, name: str) -> tuple[str, int]:
    register = client.post(
        "/auth/register",
        json={"email": email, "phone": phone, "password": "Secret123", "name": name},
    )
    assert register.status_code == 200, register.text
    user_id = register.json()["id"]
    login = client.post("/auth/login", json={"login": email, "password": "Secret123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"], user_id


def get_only_team_id(client, token: str) -> int:
    teams = client.get("/teams", headers={"Authorization": f"Bearer {token}"})
    assert teams.status_code == 200
    payload = teams.json()
    assert len(payload) == 1
    return payload[0]["id"]


def create_connection(db: Session, team_id: int, user_id: int, *, provider: str = "WB", name: str = "Main") -> MarketplaceConnection:
    connection = MarketplaceConnection(
        team_id=team_id,
        provider=provider,
        name=name,
        status="ACTIVE",
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
        is_disabled=False,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def create_product_facts(db: Session, team_id: int, connection_id: int) -> None:
    db.add_all(
        [
            AnalyticsProductFact(
                team_id=team_id,
                connection_id=connection_id,
                sku="SKU-ACME-1",
                brand="Acme",
                category="Shoes",
                warehouse="MSK-1",
                orders_count=10,
                revenue_amount=10000,
            ),
            AnalyticsProductFact(
                team_id=team_id,
                connection_id=connection_id,
                sku="SKU-BETA-1",
                brand="Beta",
                category="Bags",
                warehouse="SPB-2",
                orders_count=7,
                revenue_amount=7000,
            ),
        ]
    )
    db.commit()


def test_register_bootstraps_default_team(db: Session, client):
    client.post(
        "/auth/register",
        json={"email": "owner@example.com", "phone": "+79992223344", "password": "Secret123", "name": "Owner"},
    )
    team = db.execute(select(Team).where(Team.slug == "owner")).scalar_one_or_none()
    assert team is not None
    membership = db.execute(select(TeamMember).where(TeamMember.team_id == team.id)).scalar_one_or_none()
    assert membership is not None
    assert membership.role == TeamRole.owner.value


def test_teams_api_returns_user_teams(client):
    token, _ = register_and_login(client, email="teams@example.com", phone="+79993334455", name="Teams User")
    team_id = get_only_team_id(client, token)
    members = client.get(f"/teams/{team_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert members.status_code == 200
    assert len(members.json()) == 1


def test_owner_can_invite_and_member_can_accept(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner2@example.com", phone="+79995556677", name="Owner2")
    member_token, member_user_id = register_and_login(client, email="member@example.com", phone="+79990000011", name="Member")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "member@example.com", "role": "ANALYST"},
    )
    assert invite.status_code == 200, invite.text
    invite_id = invite.json()["id"]

    accept = client.post(
        f"/teams/{team_id}/invites/{invite_id}/accept",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert accept.status_code == 200, accept.text

    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == member_user_id)
        .first()
    )
    assert membership is not None
    assert membership.role == TeamRole.analyst.value
    assert membership.status == TeamMemberStatus.active.value


def test_admin_can_invite_member_if_allowed(client):
    owner_token, _ = register_and_login(client, email="owner-admin@example.com", phone="+79995556688", name="OwnerAdmin")
    admin_token, _ = register_and_login(client, email="admin@example.com", phone="+79995556689", name="Admin")
    team_id = get_only_team_id(client, owner_token)

    owner_invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "admin@example.com", "role": "ADMIN"},
    )
    accept = client.post(f"/teams/{team_id}/invites/{owner_invite.json()['id']}/accept", headers={"Authorization": f"Bearer {admin_token}"})
    assert accept.status_code == 200

    admin_invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "candidate@example.com", "role": "VIEWER"},
    )
    assert admin_invite.status_code == 200


def test_analyst_cannot_invite_member(client):
    owner_token, _ = register_and_login(client, email="owner3@example.com", phone="+79997778899", name="Owner3")
    analyst_token, _ = register_and_login(client, email="analyst@example.com", phone="+79990000012", name="Analyst")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "analyst@example.com", "role": "ANALYST"},
    )
    invite_id = invite.json()["id"]
    accept = client.post(f"/teams/{team_id}/invites/{invite_id}/accept", headers={"Authorization": f"Bearer {analyst_token}"})
    assert accept.status_code == 200

    denied = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"email": "newuser@example.com", "role": "VIEWER"},
    )
    assert denied.status_code == 403


def test_removed_member_cannot_access_team_api(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner4@example.com", phone="+79990000013", name="Owner4")
    viewer_token, viewer_user_id = register_and_login(client, email="viewer@example.com", phone="+79990000014", name="Viewer")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer@example.com", "role": "VIEWER"},
    )
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {viewer_token}"})
    assert accept.status_code == 200

    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == viewer_user_id)
        .first()
    )
    assert membership is not None
    remove = client.delete(f"/teams/{team_id}/members/{membership.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert remove.status_code == 200

    denied = client.get(f"/teams/{team_id}/members", headers={"Authorization": f"Bearer {viewer_token}"})
    assert denied.status_code == 403


def test_suspended_member_gets_403(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner5@example.com", phone="+79990000015", name="Owner5")
    manager_token, manager_user_id = register_and_login(client, email="manager@example.com", phone="+79990000016", name="Manager")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager@example.com", "role": "MANAGER"},
    )
    client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})

    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert membership is not None
    suspend = client.patch(
        f"/teams/{team_id}/members/{membership.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "SUSPENDED"},
    )
    assert suspend.status_code == 200

    denied = client.get(f"/teams/{team_id}/members", headers={"Authorization": f"Bearer {manager_token}"})
    assert denied.status_code == 403


def test_cross_team_access_denied(client):
    token_a, _ = register_and_login(client, email="a@example.com", phone="+79990000017", name="A")
    token_b, _ = register_and_login(client, email="b@example.com", phone="+79990000018", name="B")
    team_id_a = get_only_team_id(client, token_a)

    denied = client.get(f"/teams/{team_id_a}/members", headers={"Authorization": f"Bearer {token_b}"})
    assert denied.status_code == 403


def test_audit_events_are_written_for_iam(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner6@example.com", phone="+79990000019", name="Owner6")
    member_token, _ = register_and_login(client, email="member2@example.com", phone="+79990000020", name="Member2")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "member2@example.com", "role": "VIEWER"},
    )
    invite_id = invite.json()["id"]
    client.post(f"/teams/{team_id}/invites/{invite_id}/accept", headers={"Authorization": f"Bearer {member_token}"})
    audit = client.get(f"/teams/{team_id}/audit", headers={"Authorization": f"Bearer {owner_token}"})
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert "team.member.invited" in actions
    assert "team.member.accepted" in actions
    rows = db.query(AuditEvent).filter(AuditEvent.team_id == team_id).all()
    assert rows


def test_platform_me_requires_role_assignment(db: Session, client):
    token, user_id = register_and_login(client, email="platform@example.com", phone="+79994445566", name="Platform")

    denied = client.get("/platform/me", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403

    db.add(
        PlatformRoleAssignment(
            user_id=user_id,
            role=PlatformRole.support_admin.value,
            status="ACTIVE",
        )
    )
    db.commit()

    allowed = client.get("/platform/me", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200
    assert allowed.json()["role"] == PlatformRole.support_admin.value


def test_platform_readonly_endpoints_for_support_admin(db: Session, client):
    token, user_id = register_and_login(client, email="platform2@example.com", phone="+79994445567", name="Platform2")
    db.add(
        PlatformRoleAssignment(
            user_id=user_id,
            role=PlatformRole.support_admin.value,
            status="ACTIVE",
        )
    )
    db.commit()

    users = client.get("/platform/users", headers={"Authorization": f"Bearer {token}"})
    teams = client.get("/platform/teams", headers={"Authorization": f"Bearer {token}"})
    tickets = client.get("/platform/support/tickets", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    assert teams.status_code == 200
    assert tickets.status_code == 200


def test_platform_users_contains_messenger_and_registration_fields(db: Session, client):
    token, user_id = register_and_login(client, email="platform-users@example.com", phone="+79994445569", name="PlatformUsers")
    db.add(
        PlatformRoleAssignment(
            user_id=user_id,
            role=PlatformRole.support_admin.value,
            status="ACTIVE",
        )
    )
    db.add(
        MessengerAccountLink(
            user_id=user_id,
            provider="telegram",
            external_user_id="tg-1",
            handle="@platform_user",
            is_verified=True,
        )
    )
    db.add(
        MessengerAccountLink(
            user_id=user_id,
            provider="max",
            external_user_id="max-1",
            handle="max-platform",
            is_verified=True,
        )
    )
    db.commit()

    users = client.get("/platform/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    row = next(item for item in users.json() if item["id"] == user_id)
    assert row["email"] == "platform-users@example.com"
    assert row["telegram"] == "@platform_user"
    assert row["max"] == "max-platform"
    assert "registered_at" in row


def test_support_specialist_cannot_read_platform_audit(db: Session, client):
    token, user_id = register_and_login(client, email="platform3@example.com", phone="+79994445568", name="Platform3")
    db.add(
        PlatformRoleAssignment(
            user_id=user_id,
            role=PlatformRole.support_specialist.value,
            status="ACTIVE",
        )
    )
    db.commit()

    denied = client.get("/platform/audit", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403


def test_viewer_cannot_manage_connection_access(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner7@example.com", phone="+79990000021", name="Owner7")
    viewer_token, viewer_user_id = register_and_login(client, email="viewer2@example.com", phone="+79990000022", name="Viewer2")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer2@example.com", "role": "VIEWER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {viewer_token}"})
    assert accept.status_code == 200

    viewer_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == viewer_user_id)
        .first()
    )
    assert viewer_member is not None
    connection = create_connection(db, team_id, owner_user_id, name="Viewer Access Test")

    denied = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"team_member_id": viewer_member.id, "access_mode": "FULL"},
    )
    assert denied.status_code == 403


def test_viewer_cannot_create_connection(client):
    owner_token, _ = register_and_login(client, email="owner9@example.com", phone="+79990000027", name="Owner9")
    viewer_token, _ = register_and_login(client, email="viewer3@example.com", phone="+79990000028", name="Viewer3")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer3@example.com", "role": "VIEWER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {viewer_token}"})
    assert accept.status_code == 200

    denied = client.post(
        f"/teams/{team_id}/connections",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"provider": "WB", "name": "Viewer Should Not Create"},
    )
    assert denied.status_code == 403


def test_owner_can_crud_connection_and_audit(client):
    owner_token, _ = register_and_login(client, email="owner10@example.com", phone="+79990000029", name="Owner10")
    team_id = get_only_team_id(client, owner_token)

    create = client.post(
        f"/teams/{team_id}/connections",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"provider": "WB", "name": "Primary"},
    )
    assert create.status_code == 200, create.text
    connection_id = create.json()["id"]
    assert create.json()["status"] == "ACTIVE"

    patch = client.patch(
        f"/teams/{team_id}/connections/{connection_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Primary Renamed", "status": "ERROR"},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "Primary Renamed"
    assert patch.json()["status"] == "ERROR"

    list_connections = client.get(f"/teams/{team_id}/connections", headers={"Authorization": f"Bearer {owner_token}"})
    assert list_connections.status_code == 200
    assert len(list_connections.json()) == 1

    delete = client.delete(f"/teams/{team_id}/connections/{connection_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert delete.status_code == 200

    audit = client.get(f"/teams/{team_id}/audit", headers={"Authorization": f"Bearer {owner_token}"})
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert "connection.created" in actions
    assert "connection.updated" in actions
    assert "connection.deleted" in actions


def test_owner_can_manage_connection_access_and_scopes(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner8@example.com", phone="+79990000023", name="Owner8")
    manager_token, manager_user_id = register_and_login(client, email="manager2@example.com", phone="+79990000024", name="Manager2")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager2@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    manager_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert manager_member is not None
    connection = create_connection(db, team_id, owner_user_id, name="Owner Access Test")

    grant = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_member_id": manager_member.id, "access_mode": "SCOPED"},
    )
    assert grant.status_code == 200, grant.text
    access_id = grant.json()["id"]

    scope = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"subject_type": "BRAND", "subject_value": "Acme"},
    )
    assert scope.status_code == 200, scope.text
    scope_id = scope.json()["id"]

    scopes_list = client.get(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert scopes_list.status_code == 200
    assert len(scopes_list.json()) == 1

    patch_scope = client.patch(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes/{scope_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"subject_type": "CATEGORY", "subject_value": "Shoes"},
    )
    assert patch_scope.status_code == 200
    assert patch_scope.json()["subject_type"] == "CATEGORY"

    access_list = client.get(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert access_list.status_code == 200
    assert len(access_list.json()) == 1

    drop_scope = client.delete(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes/{scope_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert drop_scope.status_code == 200

    drop_access = client.delete(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert drop_access.status_code == 200

    audit = client.get(f"/teams/{team_id}/audit", headers={"Authorization": f"Bearer {owner_token}"})
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert "connection.access.granted" in actions
    assert "scope.created" in actions
    assert "connection.access.revoked" in actions


def test_cross_team_connection_access_returns_404(db: Session, client):
    owner_a_token, owner_a_user_id = register_and_login(client, email="owner-a@example.com", phone="+79990000025", name="OwnerA")
    owner_b_token, _ = register_and_login(client, email="owner-b@example.com", phone="+79990000026", name="OwnerB")
    team_a_id = get_only_team_id(client, owner_a_token)
    team_b_id = get_only_team_id(client, owner_b_token)
    connection_a = create_connection(db, team_a_id, owner_a_user_id, name="Team A Connection")

    denied = client.get(
        f"/teams/{team_b_id}/connections/{connection_a.id}/access",
        headers={"Authorization": f"Bearer {owner_b_token}"},
    )
    assert denied.status_code == 404


def test_scoped_user_sees_only_allowed_analytics_rows(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner11@example.com", phone="+79990000030", name="Owner11")
    manager_token, manager_user_id = register_and_login(client, email="manager3@example.com", phone="+79990000031", name="Manager3")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager3@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    manager_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert manager_member is not None

    connection = create_connection(db, team_id, owner_user_id, name="Scoped Analytics")
    create_product_facts(db, team_id, connection.id)

    grant = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_member_id": manager_member.id, "access_mode": "SCOPED"},
    )
    assert grant.status_code == 200
    access_id = grant.json()["id"]
    scope = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"subject_type": "BRAND", "subject_value": "Acme"},
    )
    assert scope.status_code == 200

    analytics = client.get(
        f"/teams/{team_id}/analytics/products?connection_id={connection.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert analytics.status_code == 200, analytics.text
    rows = analytics.json()
    assert len(rows) == 1
    assert rows[0]["brand"] == "Acme"


def test_scoped_export_contains_only_allowed_rows(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner12@example.com", phone="+79990000032", name="Owner12")
    manager_token, manager_user_id = register_and_login(client, email="manager4@example.com", phone="+79990000033", name="Manager4")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager4@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    manager_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert manager_member is not None

    connection = create_connection(db, team_id, owner_user_id, name="Scoped Export")
    create_product_facts(db, team_id, connection.id)

    grant = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_member_id": manager_member.id, "access_mode": "SCOPED"},
    )
    assert grant.status_code == 200
    access_id = grant.json()["id"]
    scope = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access/{access_id}/scopes",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"subject_type": "CATEGORY", "subject_value": "Shoes"},
    )
    assert scope.status_code == 200

    export = client.get(
        f"/teams/{team_id}/analytics/products/export.csv?connection_id={connection.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert export.status_code == 200
    body = export.text
    assert "SKU-ACME-1" in body
    assert "SKU-BETA-1" not in body


def test_analytics_denied_attempt_writes_audit(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner13@example.com", phone="+79990000034", name="Owner13")
    viewer_token, _ = register_and_login(client, email="viewer4@example.com", phone="+79990000035", name="Viewer4")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer4@example.com", "role": "VIEWER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {viewer_token}"})
    assert accept.status_code == 200

    connection = create_connection(db, team_id, owner_user_id, name="Denied Audit")
    denied = client.get(
        f"/teams/{team_id}/analytics/products?connection_id={connection.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert denied.status_code == 403

    audit = client.get(f"/teams/{team_id}/audit", headers={"Authorization": f"Bearer {owner_token}"})
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert "access.denied" in actions


def test_agent_chat_denied_for_viewer_and_logged(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner14@example.com", phone="+79990000036", name="Owner14")
    viewer_token, _ = register_and_login(client, email="viewer5@example.com", phone="+79990000037", name="Viewer5")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer5@example.com", "role": "VIEWER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {viewer_token}"})
    assert accept.status_code == 200

    denied = client.post(
        "/agent/chat",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"team_id": team_id, "message": "hello", "execute_tool": False},
    )
    assert denied.status_code == 403

    audit = client.get(f"/teams/{team_id}/audit", headers={"Authorization": f"Bearer {owner_token}"})
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert "access.denied" in actions


def test_agent_tool_execute_denied_for_manager(db: Session, client):
    owner_token, _ = register_and_login(client, email="owner15@example.com", phone="+79990000038", name="Owner15")
    manager_token, _ = register_and_login(client, email="manager5@example.com", phone="+79990000039", name="Manager5")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager5@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    denied = client.post(
        "/agent/chat",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"team_id": team_id, "message": "run tool", "execute_tool": True, "write_mode": True},
    )
    assert denied.status_code == 403


def test_agent_chat_context_for_owner_with_connection_scope(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner16@example.com", phone="+79990000040", name="Owner16")
    team_id = get_only_team_id(client, owner_token)
    connection = create_connection(db, team_id, owner_user_id, name="Agent Scoped")
    create_product_facts(db, team_id, connection.id)

    allowed = client.post(
        "/agent/chat",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_id": team_id, "connection_id": connection.id, "message": "status", "execute_tool": True, "write_mode": True},
    )
    assert allowed.status_code == 200, allowed.text
    payload = allowed.json()
    assert payload["message"] == "Agent request accepted"
    assert payload["context"]["team_id"] == team_id
    assert payload["context"]["connection_id"] == connection.id
    assert "agent.tools.execute" in payload["context"]["permissions"]


def test_agent_chat_cross_team_denied(db: Session, client):
    token_a, _ = register_and_login(client, email="owner17@example.com", phone="+79990000041", name="Owner17")
    token_b, _ = register_and_login(client, email="owner18@example.com", phone="+79990000042", name="Owner18")
    team_id_a = get_only_team_id(client, token_a)

    denied = client.post(
        "/agent/chat",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"team_id": team_id_a, "message": "cross-team"},
    )
    assert denied.status_code == 403


def test_manager_can_run_sync_only_for_allowed_connection(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner19@example.com", phone="+79990000043", name="Owner19")
    manager_token, manager_user_id = register_and_login(client, email="manager6@example.com", phone="+79990000044", name="Manager6")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager6@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    manager_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert manager_member is not None

    allowed_connection = create_connection(db, team_id, owner_user_id, name="Allowed Sync")
    denied_connection = create_connection(db, team_id, owner_user_id, name="Denied Sync")

    grant = client.post(
        f"/teams/{team_id}/connections/{allowed_connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_member_id": manager_member.id, "access_mode": "FULL"},
    )
    assert grant.status_code == 200

    allowed_sync = client.post(
        f"/teams/{team_id}/connections/{allowed_connection.id}/sync/run",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"dry_run": True},
    )
    assert allowed_sync.status_code == 200, allowed_sync.text

    denied_sync = client.post(
        f"/teams/{team_id}/connections/{denied_connection.id}/sync/run",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"dry_run": True},
    )
    assert denied_sync.status_code == 403


def test_cost_import_scoped_by_team_and_connection(db: Session, client):
    owner_token, owner_user_id = register_and_login(client, email="owner20@example.com", phone="+79990000045", name="Owner20")
    manager_token, manager_user_id = register_and_login(client, email="manager7@example.com", phone="+79990000046", name="Manager7")
    team_id = get_only_team_id(client, owner_token)

    invite = client.post(
        f"/teams/{team_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "manager7@example.com", "role": "MANAGER"},
    )
    assert invite.status_code == 200
    accept = client.post(f"/teams/{team_id}/invites/{invite.json()['id']}/accept", headers={"Authorization": f"Bearer {manager_token}"})
    assert accept.status_code == 200

    manager_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .filter(TeamMember.user_id == manager_user_id)
        .first()
    )
    assert manager_member is not None
    connection = create_connection(db, team_id, owner_user_id, name="Costs Scoped")

    grant = client.post(
        f"/teams/{team_id}/connections/{connection.id}/access",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"team_member_id": manager_member.id, "access_mode": "FULL"},
    )
    assert grant.status_code == 200

    imported = client.post(
        f"/teams/{team_id}/connections/{connection.id}/costs/import",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"file_name": "costs.csv", "total_rows": 10, "accepted_rows": 9, "rejected_rows": 1},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["connection_id"] == connection.id

    denied_rows = client.post(
        f"/teams/{team_id}/connections/{connection.id}/costs/import",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"file_name": "bad.csv", "total_rows": 1, "accepted_rows": 2, "rejected_rows": 0},
    )
    assert denied_rows.status_code == 422


def test_platform_admin_can_manage_recommendations_and_team_dashboard_reads_them(db: Session, client):
    admin_token, admin_user_id = register_and_login(client, email="platform4@example.com", phone="+79990000047", name="Platform4")
    owner_token, owner_user_id = register_and_login(client, email="owner21@example.com", phone="+79990000048", name="Owner21")
    team_id = get_only_team_id(client, owner_token)
    connection = create_connection(db, team_id, owner_user_id, provider="WB", name="WB Main")
    create_product_facts(db, team_id, connection.id)

    db.add(
        PlatformRoleAssignment(
            user_id=admin_user_id,
            role=PlatformRole.platform_admin.value,
            status="ACTIVE",
        )
    )
    db.commit()

    created = client.post(
        "/platform/recommendations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Проверьте логистику",
            "body": "Снизьте расходы через анализ поставок по складам.",
            "cta_label": "Открыть аналитику",
            "cta_href": "/dashboard",
            "priority": 10,
            "target_marketplace": "WB",
            "is_active": True,
        },
    )
    assert created.status_code == 200, created.text
    rec_id = created.json()["id"]

    listed = client.get("/platform/recommendations", headers={"Authorization": f"Bearer {admin_token}"})
    assert listed.status_code == 200
    assert any(row["id"] == rec_id for row in listed.json())

    dashboard = client.get(
        f"/teams/{team_id}/dashboard?connection_id={connection.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert payload["products_total"] >= 1
    assert any(item["id"] == rec_id for item in payload["recommendations"])

    patched = client.patch(
        f"/platform/recommendations/{rec_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert patched.status_code == 200

    disabled = db.get(DashboardRecommendation, rec_id)
    assert disabled is not None
    assert disabled.is_active is False
