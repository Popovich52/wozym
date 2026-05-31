from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, utcnow
from app.core.security import (
    create_access_token,
    generate_email_token,
    generate_phone_code,
    generate_refresh_token,
    hash_password,
    hash_token,
    normalize_email,
    normalize_phone,
    validate_password_policy,
    verify_password,
)
from app.deps import get_current_user
from app.models import EmailVerificationToken, PhoneVerificationCode, SessionModel, Team, TeamMember, TeamMemberStatus, TeamRole, User
from app.schemas import (
    AuthTokensOut,
    LoginRequest,
    MessageOut,
    RegisterRequest,
    UserOut,
    VerifyEmailRequest,
    VerifyPhoneRequest,
)
from app.services import add_audit, log_phone_code, send_email


router = APIRouter(prefix="/auth", tags=["auth"])


slug_re = re.compile(r"[^a-z0-9]+")


def is_expired(value: datetime) -> bool:
    now_utc = datetime.now(tz=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc) <= now_utc
    return value <= now_utc


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/")


def make_team_slug(seed: str, fallback: str) -> str:
    raw = slug_re.sub("-", seed.lower()).strip("-")
    if not raw:
        raw = fallback
    return raw[:48]


def create_default_team(db: Session, user: User) -> Team:
    seed = user.email.split("@", 1)[0]
    candidate = make_team_slug(seed, f"user-{user.id}")
    slug = candidate
    suffix = 2
    while db.execute(select(Team).where(Team.slug == slug)).scalar_one_or_none() is not None:
        slug = f"{candidate}-{suffix}"
        suffix += 1

    team = Team(
        slug=slug,
        name=f"{user.name or seed}'s Team",
        created_by_user_id=user.id,
        is_active=True,
    )
    db.add(team)
    db.flush()

    member = TeamMember(
        team_id=team.id,
        user_id=user.id,
        role=TeamRole.owner.value,
        status=TeamMemberStatus.active.value,
    )
    db.add(member)
    return team


@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserOut:
    email = normalize_email(payload.email)
    try:
        phone = normalize_phone(payload.phone)
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    exists = db.execute(select(User).where(or_(User.email == email, User.phone == phone))).scalar_one_or_none()
    if exists is not None:
        if exists.email == email:
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=409, detail="Phone already registered")

    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password(payload.password),
        name=payload.name,
        status="active",
    )
    db.add(user)
    db.flush()
    team = create_default_team(db, user)

    email_token = generate_email_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(email_token),
            expires_at=utcnow() + timedelta(hours=24),
        )
    )
    code = generate_phone_code()
    db.add(
        PhoneVerificationCode(
            user_id=user.id,
            code_hash=hash_token(code),
            expires_at=utcnow() + timedelta(minutes=10),
            attempts=0,
        )
    )

    verify_link = f"{settings.web_url}/verify-email?token={email_token}"
    send_email(user.email, "Verify your email", f"Open link to verify your email: {verify_link}")
    log_phone_code(user.phone, code)

    add_audit(
        db,
        "auth.register",
        user.id,
        request.client.host if request.client else None,
        team_id=team.id,
        resource_type="team",
        resource_id=str(team.id),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=AuthTokensOut)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthTokensOut:
    login_value = payload.login.strip()
    if "@" in login_value:
        criteria = User.email == normalize_email(login_value)
    else:
        try:
            criteria = User.phone == normalize_phone(login_value)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.execute(select(User).where(criteria)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User inactive")

    refresh_token = generate_refresh_token()
    session = SessionModel(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=utcnow() + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    db.flush()
    access_token = create_access_token(user_id=user.id, session_id=session.id)
    set_refresh_cookie(response, refresh_token)

    add_audit(db, "auth.login", user.id, request.client.host if request.client else None)
    db.commit()
    return AuthTokensOut(access_token=access_token, user=user)


@router.post("/refresh", response_model=AuthTokensOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthTokensOut:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    session = db.execute(select(SessionModel).where(SessionModel.refresh_token_hash == hash_token(refresh_token))).scalar_one_or_none()
    if session is None or session.revoked_at is not None or is_expired(session.expires_at):
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="User inactive")

    next_refresh = generate_refresh_token()
    session.refresh_token_hash = hash_token(next_refresh)
    session.expires_at = utcnow() + timedelta(days=settings.refresh_token_ttl_days)
    access_token = create_access_token(user_id=user.id, session_id=session.id)
    set_refresh_cookie(response, next_refresh)
    db.commit()

    return AuthTokensOut(access_token=access_token, user=user)


@router.post("/logout", response_model=MessageOut)
def logout(
    request: Request,
    response: Response,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, session = user_with_session
    session.revoked_at = utcnow()
    add_audit(db, "auth.logout", user.id, request.client.host if request.client else None)
    db.commit()
    clear_refresh_cookie(response)
    return MessageOut(message="Logged out")


@router.post("/verify-email", response_model=MessageOut)
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)) -> MessageOut:
    token_hash = hash_token(payload.token)
    token = db.execute(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)).scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    if token.used_at is not None:
        raise HTTPException(status_code=400, detail="Token already used")
    if is_expired(token.expires_at):
        raise HTTPException(status_code=400, detail="Token expired")

    token.used_at = utcnow()
    user = db.get(User, token.user_id)
    if user is not None:
        user.email_verified_at = utcnow()
        add_audit(db, "auth.email_verified", user.id, request.client.host if request.client else None)
    db.commit()
    return MessageOut(message="Email verified")


@router.post("/resend-email", response_model=MessageOut)
def resend_email(
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, _ = user_with_session
    token_value = generate_email_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            expires_at=utcnow() + timedelta(hours=24),
        )
    )
    db.commit()

    verify_link = f"{settings.web_url}/verify-email?token={token_value}"
    send_email(user.email, "Verify your email", f"Open link to verify your email: {verify_link}")
    add_audit(db, "auth.resend_email", user.id, request.client.host if request.client else None)
    return MessageOut(message="Verification email sent")


@router.post("/verify-phone", response_model=MessageOut)
def verify_phone(
    payload: VerifyPhoneRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, _ = user_with_session
    code = db.execute(
        select(PhoneVerificationCode)
        .where(PhoneVerificationCode.user_id == user.id)
        .where(PhoneVerificationCode.used_at.is_(None))
        .order_by(PhoneVerificationCode.created_at.desc())
    ).scalars().first()
    if code is None:
        raise HTTPException(status_code=400, detail="No verification code")
    if is_expired(code.expires_at):
        raise HTTPException(status_code=400, detail="Code expired")

    if code.code_hash != hash_token(payload.code):
        code.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid code")

    code.used_at = utcnow()
    user.phone_verified_at = utcnow()
    add_audit(db, "auth.phone_verified", user.id, request.client.host if request.client else None)
    db.commit()
    return MessageOut(message="Phone verified")


@router.post("/resend-phone", response_model=MessageOut)
def resend_phone(
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, _ = user_with_session
    code_value = generate_phone_code()
    db.add(
        PhoneVerificationCode(
            user_id=user.id,
            code_hash=hash_token(code_value),
            expires_at=utcnow() + timedelta(minutes=10),
            attempts=0,
        )
    )
    db.commit()
    log_phone_code(user.phone, code_value)
    add_audit(db, "auth.resend_phone", user.id, request.client.host if request.client else None)
    return MessageOut(message="Phone verification code sent")
