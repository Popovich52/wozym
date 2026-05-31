from __future__ import annotations

from fastapi import APIRouter

from app.schemas import MessageOut


router = APIRouter(prefix="/messengers", tags=["messengers"])


@router.post("/link/start", response_model=MessageOut)
def link_start() -> MessageOut:
    return MessageOut(message="TODO: Telegram/MAX link start endpoint")


@router.post("/link/complete", response_model=MessageOut)
def link_complete() -> MessageOut:
    return MessageOut(message="TODO: Telegram/MAX link complete endpoint")
