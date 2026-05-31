from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AiGenerationLog, AiGenerationStatus


MAX_JSON_STRING_LENGTH = 4_000


def _trim_value(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("data:image/") or value.startswith("data:video/"):
            return value[:80] + "...<data-url-truncated>"
        if len(value) > MAX_JSON_STRING_LENGTH:
            return value[:MAX_JSON_STRING_LENGTH] + "...<truncated>"
        return value
    if isinstance(value, list):
        return [_trim_value(item) for item in value[:100]]
    if isinstance(value, dict):
        return {str(key): _trim_value(item) for key, item in list(value.items())[:100]}
    return value


def sanitize_ai_log_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return _trim_value(payload)


def create_ai_generation_log(
    db: Session,
    *,
    operation: str,
    team_id: int | None = None,
    connection_id: int | None = None,
    product_row_id: int | None = None,
    user_id: int | None = None,
    status: str = AiGenerationStatus.queued.value,
    request_payload: dict[str, Any] | None = None,
    trace_id: str | None = None,
    image_count: int = 0,
) -> AiGenerationLog:
    now = datetime.now(tz=timezone.utc)
    row = AiGenerationLog(
        team_id=team_id,
        connection_id=connection_id,
        product_row_id=product_row_id,
        user_id=user_id,
        provider=settings.ai_provider,
        operation=operation,
        status=status,
        model_text=settings.ai_text_model,
        model_vision=settings.ai_vision_model,
        model_image=settings.ai_image_model if settings.ai_enable_image_generation else None,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cached_input_tokens=0,
        reasoning_tokens=0,
        image_count=max(0, image_count),
        output_asset_count=0,
        trace_id=trace_id,
        request=sanitize_ai_log_payload(request_payload),
        response=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def finish_ai_generation_log(
    db: Session,
    row: AiGenerationLog,
    *,
    status: str,
    response_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    cached_input_tokens: int = 0,
    reasoning_tokens: int = 0,
    output_asset_count: int = 0,
    estimated_cost_microusd: int | None = None,
    latency_ms: int | None = None,
) -> AiGenerationLog:
    row.status = status
    row.response = sanitize_ai_log_payload(response_payload)
    row.error_message = error_message[:2_000] if error_message else None
    row.prompt_tokens = max(0, prompt_tokens)
    row.completion_tokens = max(0, completion_tokens)
    row.total_tokens = max(0, total_tokens)
    row.cached_input_tokens = max(0, cached_input_tokens)
    row.reasoning_tokens = max(0, reasoning_tokens)
    row.output_asset_count = max(0, output_asset_count)
    row.estimated_cost_microusd = estimated_cost_microusd
    row.latency_ms = latency_ms
    row.updated_at = datetime.now(tz=timezone.utc)
    db.flush()
    return row
