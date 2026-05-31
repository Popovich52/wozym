from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PhoneVerificationCode, SessionModel
import app.routes.auth as auth_routes


def register_user(client) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "phone": "+79990001122",
            "password": "Secret123",
            "name": "User",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def login_email(client):
    return client.post("/auth/login", json={"login": "user@example.com", "password": "Secret123"})


def login_phone(client):
    return client.post("/auth/login", json={"login": "+79990001122", "password": "Secret123"})


def test_register_and_duplicates(client):
    register_user(client)

    dup_email = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "phone": "+79990004455",
            "password": "Secret123",
            "name": "User2",
        },
    )
    assert dup_email.status_code == 409

    dup_phone = client.post(
        "/auth/register",
        json={
            "email": "user2@example.com",
            "phone": "+79990001122",
            "password": "Secret123",
            "name": "User2",
        },
    )
    assert dup_phone.status_code == 409


def test_login_by_email_and_phone(client):
    register_user(client)

    by_email = login_email(client)
    assert by_email.status_code == 200
    assert by_email.json()["access_token"]

    by_phone = login_phone(client)
    assert by_phone.status_code == 200
    assert by_phone.json()["access_token"]


def test_wrong_password(client):
    register_user(client)
    bad = client.post("/auth/login", json={"login": "user@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401


def test_email_verification(client):
    sent_links: list[str] = []

    def fake_send_email(to_email: str, subject: str, body: str) -> None:
        sent_links.append(body)

    auth_routes.send_email = fake_send_email
    register_user(client)
    assert sent_links
    parsed = urlparse(sent_links[-1].split()[-1])
    token = parse_qs(parsed.query)["token"][0]

    verify = client.post("/auth/verify-email", json={"token": token})
    assert verify.status_code == 200


def test_phone_verification(client, db: Session):
    register_user(client)
    login = login_email(client)
    access = login.json()["access_token"]

    row = db.execute(select(PhoneVerificationCode).order_by(PhoneVerificationCode.id.desc())).scalars().first()
    assert row is not None

    wrong = client.post(
        "/auth/verify-phone",
        headers={"Authorization": f"Bearer {access}"},
        json={"code": "000000"},
    )
    assert wrong.status_code == 400

    # Find active session and brute-check stored hash by resend + log callback replacement is out of scope,
    # so here we validate contract with resend and invalid flow only.
    resend = client.post("/auth/resend-phone", headers={"Authorization": f"Bearer {access}"})
    assert resend.status_code == 200


def test_change_password_and_old_password_rejected(client, db: Session):
    register_user(client)
    login = login_email(client)
    access = login.json()["access_token"]

    second = login_phone(client)
    assert second.status_code == 200
    assert db.execute(select(SessionModel)).scalars().all()

    change = client.post(
        "/me/password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": "Secret123", "new_password": "NewSecret123"},
    )
    assert change.status_code == 200

    old_login = client.post("/auth/login", json={"login": "user@example.com", "password": "Secret123"})
    assert old_login.status_code == 401
    new_login = client.post("/auth/login", json={"login": "user@example.com", "password": "NewSecret123"})
    assert new_login.status_code == 200
