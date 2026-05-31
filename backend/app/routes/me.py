from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, utcnow
from app.core.security import validate_password_policy, verify_password, hash_password
from app.deps import get_current_user
from app.models import SessionModel, User
from app.schemas import ChangePasswordRequest, MeUpdateRequest, MessageOut, SessionOut, UserOut
from app.services import add_audit


router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserOut)
def get_me(user_with_session: tuple[User, SessionModel] = Depends(get_current_user)) -> UserOut:
    user, _ = user_with_session
    return user


@router.patch("/me", response_model=UserOut)
def patch_me(payload: MeUpdateRequest, user_with_session: tuple[User, SessionModel] = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    user, _ = user_with_session
    user.name = payload.name.strip()
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", response_model=MessageOut)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, session = user_with_session
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is invalid")
    try:
        validate_password_policy(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    user.password_hash = hash_password(payload.new_password)
    for other in db.execute(
        select(SessionModel).where(SessionModel.user_id == user.id).where(SessionModel.id != session.id).where(SessionModel.revoked_at.is_(None))
    ).scalars():
        other.revoked_at = utcnow()

    add_audit(db, "user.password_changed", user.id, request.client.host if request.client else None)
    db.commit()
    return MessageOut(message="Password changed")


@router.get("/me/sessions", response_model=list[SessionOut])
def list_sessions(user_with_session: tuple[User, SessionModel] = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SessionOut]:
    user, _ = user_with_session
    rows = db.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user.id)
        .where(SessionModel.revoked_at.is_(None))
        .order_by(SessionModel.created_at.desc())
    ).scalars()
    return list(rows)


@router.delete("/me/sessions/{session_id}", response_model=MessageOut)
def delete_session(
    session_id: int,
    user_with_session: tuple[User, SessionModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    user, current_session = user_with_session
    if session_id == current_session.id:
        raise HTTPException(status_code=400, detail="Cannot revoke current session here. Use logout.")

    session = db.get(SessionModel, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.revoked_at is None:
        session.revoked_at = utcnow()
    db.commit()
    return MessageOut(message="Session revoked")
