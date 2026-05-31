from __future__ import annotations

import base64
from io import BytesIO
import json
import mimetypes
import re
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.ai_logging import create_ai_generation_log, finish_ai_generation_log
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import AiGenerationLog, AiGenerationStatus, MarketplaceProduct


DATA_IMAGE_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)
AI_ASSET_DIR = Path(__file__).resolve().parents[1] / "runtime" / "ai-assets"
OZON_AI_IMAGE_SIZE = (900, 1200)


CARD_DRAFT_SCHEMA: dict[str, Any] = {
    "name": "product_card_ai_draft",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "photo_analysis",
            "field_checks",
            "field_recommendations",
            "media_recommendations",
            "draft",
            "prompt_analysis",
            "reference_analysis",
            "template_plan",
            "warnings",
        ],
        "properties": {
            "photo_analysis": {
                "type": "object",
                "additionalProperties": False,
                "required": ["detected_product_type", "summary", "visible_features", "quality_issues", "cannot_determine"],
                "properties": {
                    "detected_product_type": {"type": "string"},
                    "summary": {"type": "string"},
                    "visible_features": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "value", "confidence", "source", "reason"],
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "confidence": {"type": "number"},
                                "source": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                    "quality_issues": {"type": "array", "items": {"type": "string"}},
                    "cannot_determine": {"type": "array", "items": {"type": "string"}},
                },
            },
            "field_checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "field",
                        "current_value",
                        "suggested_value",
                        "status",
                        "confidence",
                        "reason",
                        "requires_user_confirmation",
                    ],
                    "properties": {
                        "field": {"type": "string"},
                        "current_value": {"type": "string"},
                        "suggested_value": {"type": "string"},
                        "status": {"type": "string"},
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                        "requires_user_confirmation": {"type": "boolean"},
                    },
                },
            },
            "field_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "field",
                        "currentValue",
                        "suggestedValue",
                        "hasRecommendation",
                        "confidence",
                        "reason",
                        "source",
                        "action",
                    ],
                    "properties": {
                        "field": {"type": "string"},
                        "currentValue": {"type": "string"},
                        "suggestedValue": {"type": "string"},
                        "hasRecommendation": {"type": "boolean"},
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                        "source": {"type": "string"},
                        "action": {"type": "string"},
                    },
                },
            },
            "media_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "prompt", "reason", "confidence", "action"],
                    "properties": {
                        "type": {"type": "string"},
                        "prompt": {"type": "string"},
                        "reason": {"type": "string"},
                        "confidence": {"type": "number"},
                        "action": {"type": "string"},
                    },
                },
            },
            "draft": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "description", "annotation", "hashtags", "attributes", "questions", "content_rating_actions"],
                "properties": {
                    "title": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["value", "confidence", "reason"],
                        "properties": {
                            "value": {"type": "string"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                    },
                    "description": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["value", "confidence", "reason"],
                        "properties": {
                            "value": {"type": "string"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                    },
                    "annotation": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["value", "confidence", "reason"],
                        "properties": {
                            "value": {"type": "string"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                    },
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "attribute_id",
                                "name",
                                "value",
                                "source",
                                "confidence",
                                "requires_user_confirmation",
                                "reason",
                            ],
                            "properties": {
                                "attribute_id": {"type": "integer"},
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "source": {"type": "string"},
                                "confidence": {"type": "number"},
                                "requires_user_confirmation": {"type": "boolean"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                    "questions": {"type": "array", "items": {"type": "string"}},
                    "content_rating_actions": {"type": "array", "items": {"type": "string"}},
                },
            },
            "prompt_analysis": {
                "type": "object",
                "additionalProperties": False,
                "required": ["style_direction", "must_include", "must_avoid", "warnings"],
                "properties": {
                    "style_direction": {"type": "string"},
                    "must_include": {"type": "array", "items": {"type": "string"}},
                    "must_avoid": {"type": "array", "items": {"type": "string"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
            },
            "reference_analysis": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "style_brief", "warnings"],
                "properties": {
                    "source": {"type": "string"},
                    "style_brief": {"type": "string"},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
            },
            "template_plan": {
                "type": "object",
                "additionalProperties": False,
                "required": ["template_id", "style_direction", "cards"],
                "properties": {
                    "template_id": {"type": "string"},
                    "style_direction": {"type": "string"},
                    "cards": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["slot", "headline", "bullets", "required_fields"],
                            "properties": {
                                "slot": {"type": "string"},
                                "headline": {"type": "string"},
                                "bullets": {"type": "array", "items": {"type": "string"}},
                                "required_fields": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                },
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _truncate_json(value: Any, limit: int = 20_000) -> Any:
    rendered = json.dumps(value, ensure_ascii=False, default=str)
    if len(rendered) <= limit:
        return value
    return {"truncated": True, "preview": rendered[:limit]}


def build_product_card_context(row: MarketplaceProduct, *, current_fields: dict[str, Any], image_urls: list[str]) -> dict[str, Any]:
    payload = _as_record(row.payload)
    info_item = _as_record(payload.get("info_item"))
    attributes_item = _as_record(payload.get("attributes_item"))
    content_rating = _as_record(payload.get("content_rating"))
    selected_images = image_urls or _as_list(row.image_urls)
    selected_images = [str(url).strip() for url in selected_images if str(url or "").strip()][: settings.ai_max_images_per_draft]
    return {
        "product": {
            "row_id": row.id,
            "provider": row.provider,
            "external_product_id": row.external_product_id,
            "offer_id": row.external_offer_id,
            "sku": row.external_sku,
            "barcode": row.barcode,
            "name": row.name,
            "brand": row.brand,
            "category_name": row.category_name,
            "status": row.status,
            "image_count": len(row.image_urls or []),
            "video_count": len(row.video_urls or []),
        },
        "current_fields": current_fields,
        "marketplace_payload": {
            "info_item": _truncate_json(info_item),
            "attributes_item": _truncate_json(attributes_item),
        },
        "content_rating": _truncate_json(content_rating),
        "media": {
            "images": selected_images,
            "videos": _as_list(row.video_urls)[:10],
        },
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def _usage_from_response(payload: dict[str, Any]) -> dict[str, int]:
    usage = _as_record(payload.get("usage"))
    input_details = _as_record(usage.get("input_tokens_details"))
    output_details = _as_record(usage.get("output_tokens_details"))
    return {
        "prompt_tokens": int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
    }


def _image_extension(mime_type: str) -> str:
    extension = mimetypes.guess_extension(mime_type.split(";")[0].strip()) or ".png"
    return ".jpg" if extension == ".jpe" else extension


def _load_local_ai_asset(source: str) -> tuple[bytes, str, str] | None:
    parsed = urlparse(source)
    if not parsed.path.startswith("/ai-assets/"):
        return None
    file_name = Path(unquote(parsed.path)).name
    if not file_name:
        return None
    path = AI_ASSET_DIR / file_name
    if not path.exists() or not path.is_file():
        return None
    mime_type, _encoding = mimetypes.guess_type(path.name)
    return path.read_bytes(), mime_type or "image/jpeg", path.name


def _load_image_for_edit(client: httpx.Client, image_url: str) -> tuple[bytes, str, str]:
    source = image_url.strip()
    data_match = DATA_IMAGE_RE.match(source)
    if data_match:
        mime_type = data_match.group(1).lower()
        try:
            image_bytes = base64.b64decode(data_match.group(2), validate=True)
        except ValueError as exc:
            raise ValueError("Invalid base64 image data URL") from exc
        return image_bytes, mime_type, f"source{_image_extension(mime_type)}"

    local_asset = _load_local_ai_asset(source)
    if local_asset is not None:
        return local_asset

    lower = source.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        raise ValueError("source_image_url must be an http(s) URL or image data URL")

    response = client.get(source, follow_redirects=True)
    if response.status_code >= 400:
        raise RuntimeError(f"Не удалось загрузить исходное изображение: HTTP {response.status_code}")
    mime_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if not mime_type.startswith("image/"):
        guessed_type, _encoding = mimetypes.guess_type(source)
        mime_type = guessed_type or "image/png"
    return response.content, mime_type, f"source{_image_extension(mime_type)}"


def _image_bytes_to_openai_data_url(image_bytes: bytes, mime_type: str) -> str:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            normalized = ImageOps.exif_transpose(image)
            if normalized.mode in {"RGBA", "LA"}:
                canvas = Image.new("RGB", normalized.size, "white")
                alpha = normalized.getchannel("A")
                canvas.paste(normalized.convert("RGB"), mask=alpha)
                normalized = canvas
            else:
                normalized = normalized.convert("RGB")
            normalized.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=88, optimize=True)
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        safe_mime = mime_type if mime_type.startswith("image/") else "image/png"
        return f"data:{safe_mime};base64,{encoded}"


def _prepare_openai_image_inputs(client: httpx.Client, image_urls: list[str]) -> tuple[list[str], list[str]]:
    prepared: list[str] = []
    warnings: list[str] = []
    for image_url in image_urls[: settings.ai_max_images_per_draft]:
        source = str(image_url or "").strip()
        if not source:
            continue
        try:
            image_bytes, mime_type, _file_name = _load_image_for_edit(client, source)
            prepared.append(_image_bytes_to_openai_data_url(image_bytes, mime_type))
        except Exception as exc:
            warnings.append(f"Не удалось подготовить изображение для AI-анализа: {source[:160]} ({exc})")
    return prepared, warnings


def _build_media_edit_prompt(*, product_name: str | None, user_prompt: str, reference: dict[str, Any]) -> str:
    reference_note = str(reference.get("note") or reference.get("description") or reference.get("style") or "").strip()
    product_context = f"Товар: {product_name}." if product_name else "Товар взят с исходного изображения."
    parts = [
        "Create a marketplace-ready product card image by editing the provided product photo.",
        product_context,
        "Keep the real product shape, color, proportions, and visible material accurate.",
        "Do not invent logos, certifications, brand names, claims, text labels, dimensions, or technical specs unless explicitly present in the prompt.",
        "Make the result clean, premium, and suitable for an Ozon marketplace gallery image.",
        f"User instruction: {user_prompt.strip()}",
    ]
    if reference_note:
        parts.append(f"Reference/style direction: {reference_note}")
    return "\n".join(parts)


def _extract_generated_image(payload: dict[str, Any], *, output_format: str) -> tuple[str, str | None]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("OpenAI image response did not contain image data")
    first = data[0] if isinstance(data[0], dict) else {}
    revised_prompt = first.get("revised_prompt") if isinstance(first.get("revised_prompt"), str) else None
    url = first.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip(), revised_prompt
    b64_json = first.get("b64_json")
    if isinstance(b64_json, str) and b64_json.strip():
        fmt = output_format.strip().lower() or "png"
        mime_type = "image/jpeg" if fmt in {"jpg", "jpeg"} else f"image/{fmt}"
        return f"data:{mime_type};base64,{b64_json.strip()}", revised_prompt
    raise RuntimeError("OpenAI image response did not include url or b64_json")


def _persist_generated_image(image_url: str, *, log_id: int, output_format: str) -> str:
    data_match = DATA_IMAGE_RE.match(image_url)
    if not data_match:
        return image_url
    image_bytes = base64.b64decode(data_match.group(2))
    with Image.open(BytesIO(image_bytes)) as image:
        normalized = ImageOps.exif_transpose(image)
        if normalized.mode in {"RGBA", "LA"}:
            canvas = Image.new("RGB", normalized.size, "white")
            alpha = normalized.getchannel("A") if normalized.mode == "RGBA" else normalized.getchannel("A")
            canvas.paste(normalized.convert("RGB"), mask=alpha)
            normalized = canvas
        else:
            normalized = normalized.convert("RGB")
        normalized.thumbnail(OZON_AI_IMAGE_SIZE, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", OZON_AI_IMAGE_SIZE, "white")
        left = (OZON_AI_IMAGE_SIZE[0] - normalized.width) // 2
        top = (OZON_AI_IMAGE_SIZE[1] - normalized.height) // 2
        canvas.paste(normalized, (left, top))
        output = BytesIO()
        canvas.save(output, format="JPEG", quality=92, optimize=True, progressive=True)
        asset_bytes = output.getvalue()
    file_name = f"ai-media-{log_id}.jpg"
    AI_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (AI_ASSET_DIR / file_name).write_bytes(asset_bytes)
    return f"{settings.api_url.rstrip('/')}/ai-assets/{file_name}"


def _validate_ai_media_image_request(*, source_image_url: str, user_prompt: str, output_format: str) -> tuple[str, str]:
    if not settings.ai_card_assistant_enabled:
        raise ValueError("AI assistant is disabled")
    if not settings.ai_enable_image_generation:
        raise ValueError("AI image generation is disabled")
    if settings.ai_provider.strip().lower() != "openai":
        raise ValueError("Unsupported AI provider")
    if not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is not configured")
    if not source_image_url.strip():
        raise ValueError("source_image_url is required")
    prompt = user_prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required")

    safe_output_format = output_format.strip().lower() or "png"
    if safe_output_format == "jpg":
        safe_output_format = "jpeg"
    if safe_output_format not in {"png", "jpeg", "webp"}:
        safe_output_format = "png"
    return prompt, safe_output_format


def _build_openai_request(
    context: dict[str, Any],
    *,
    user_prompt: str,
    template_id: str | None,
    reference: dict[str, Any],
    image_inputs: list[str] | None = None,
) -> dict[str, Any]:
    instruction = (
        "Ты AI-помощник продавца маркетплейса. Проанализируй фото и текущие данные карточки. "
        "Верни только JSON по схеме. Не придумывай юридически значимые параметры. "
        "ТН ВЭД, страна, гарантия, сертификаты, точные размеры, вес и совместимость всегда требуют подтверждения, "
        "если они не взяты из существующего payload или явно не подтверждены пользователем. "
        "Цель — повысить content rating выше 80, не портя существующие данные. "
        "Для каждого поля формы верни field_recommendations: field, currentValue, suggestedValue, hasRecommendation, confidence, reason, source, action. "
        "action используй из набора auto_apply, show_only, skip. Если hasRecommendation=false, suggestedValue должен быть пустым и action=skip. "
        "auto_apply ставь только если значение безопасно, не перезаписывает важные пользовательские данные и confidence >= 0.85. "
        "Если confidence < 0.55, action=show_only, но это низкоуверенная рекомендация для общего блока, не для inline поля. "
        "Статусы field_checks используй из набора: ok, missing, suggested, conflict, unsafe, unknown. "
        "Отдельно верни media_recommendations по текущим фото и требованиям рейтинга: главное фото, инфографика, размеры, преимущества, использование, rich-content. "
        "Для media action используй generate, show_prompt_only, skip; generate только при confidence >= 0.85."
    )
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": json.dumps(
                {
                    "instructions": instruction,
                    "user_prompt": user_prompt,
                    "template_id": template_id or "market-clean-01",
                    "reference": reference,
                    "context": context,
                },
                ensure_ascii=False,
                default=str,
            ),
        }
    ]
    for image_url in image_inputs if image_inputs is not None else _as_record(context.get("media")).get("images", []):
        url = str(image_url or "").strip()
        if not url:
            continue
        content.append({"type": "input_image", "image_url": url})

    return {
        "model": settings.ai_vision_model,
        "input": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": CARD_DRAFT_SCHEMA["name"],
                "strict": CARD_DRAFT_SCHEMA["strict"],
                "schema": CARD_DRAFT_SCHEMA["schema"],
            }
        },
    }


def generate_ai_card_draft(
    db: Session,
    *,
    row: MarketplaceProduct,
    user_id: int,
    team_id: int,
    connection_id: int,
    current_fields: dict[str, Any],
    image_urls: list[str],
    user_prompt: str,
    template_id: str | None,
    reference: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    if not settings.ai_card_assistant_enabled:
        raise ValueError("AI assistant is disabled")
    if settings.ai_provider.strip().lower() != "openai":
        raise ValueError("Unsupported AI provider")
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    context = build_product_card_context(row, current_fields=current_fields, image_urls=image_urls)
    trace_id = f"ai-card-{uuid.uuid4().hex}"
    log_row = create_ai_generation_log(
        db,
        operation="full_card_draft",
        team_id=team_id,
        connection_id=connection_id,
        product_row_id=row.id,
        user_id=user_id,
        status=AiGenerationStatus.running.value,
        trace_id=trace_id,
        image_count=len(_as_record(context.get("media")).get("images", [])),
        request_payload={
            "template_id": template_id,
            "user_prompt": user_prompt,
            "reference": reference,
            "context": context,
        },
    )
    db.commit()

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
            image_inputs, image_warnings = _prepare_openai_image_inputs(client, _as_record(context.get("media")).get("images", []))
            if image_warnings:
                media_context = _as_record(context.get("media"))
                media_context["image_prepare_warnings"] = image_warnings
                context["media"] = media_context
            if not image_inputs:
                raise RuntimeError("Не удалось подготовить ни одно изображение для AI-анализа")
            request_payload = _build_openai_request(
                context,
                user_prompt=user_prompt,
                template_id=template_id,
                reference=reference,
                image_inputs=image_inputs,
            )
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response_payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text[:2000]}
        if response.status_code >= 400:
            message = str(_as_record(response_payload.get("error")).get("message") or "OpenAI request failed")
            request_id = response.headers.get("x-request-id")
            if request_id:
                message = f"{message} (OpenAI request id: {request_id})"
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                response_payload=response_payload,
                error_message=message,
                latency_ms=latency_ms,
            )
            db.commit()
            raise RuntimeError(message)

        text = _extract_response_text(response_payload)
        if not text:
            raise RuntimeError("OpenAI response did not contain structured text")
        draft = json.loads(text)
        usage = _usage_from_response(response_payload)
        usage["model"] = str(response_payload.get("model") or settings.ai_vision_model)
        log_usage = {key: value for key, value in usage.items() if key != "model"}
        finish_ai_generation_log(
            db,
            log_row,
            status=AiGenerationStatus.success.value,
            response_payload={"draft": draft, "openai_response_id": response_payload.get("id")},
            latency_ms=latency_ms,
            **log_usage,
        )
        db.commit()
        return draft, usage, log_row.id
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        db.rollback()
        log_row = db.get(type(log_row), log_row.id)
        if log_row is not None and log_row.status != AiGenerationStatus.success.value:
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            db.commit()
        raise


def create_ai_media_image_job(
    db: Session,
    *,
    row: MarketplaceProduct,
    user_id: int,
    team_id: int,
    connection_id: int,
    source_image_url: str,
    user_prompt: str,
    reference: dict[str, Any],
    output_format: str = "png",
    size: str = "1024x1024",
) -> AiGenerationLog:
    prompt, safe_output_format = _validate_ai_media_image_request(
        source_image_url=source_image_url,
        user_prompt=user_prompt,
        output_format=output_format,
    )
    trace_id = f"ai-media-{uuid.uuid4().hex}"
    log_row = create_ai_generation_log(
        db,
        operation="media_image_edit",
        team_id=team_id,
        connection_id=connection_id,
        product_row_id=row.id,
        user_id=user_id,
        status=AiGenerationStatus.queued.value,
        trace_id=trace_id,
        image_count=1,
        request_payload={
            "source_image_url": source_image_url,
            "prompt": prompt,
            "reference": reference,
            "output_format": safe_output_format,
            "size": size,
        },
    )
    db.commit()
    db.refresh(log_row)
    return log_row


def generate_ai_media_image(
    db: Session,
    *,
    row: MarketplaceProduct,
    user_id: int,
    team_id: int,
    connection_id: int,
    source_image_url: str,
    user_prompt: str,
    reference: dict[str, Any],
    output_format: str = "png",
    size: str = "1024x1024",
) -> tuple[str, str | None, dict[str, Any], int]:
    prompt, safe_output_format = _validate_ai_media_image_request(
        source_image_url=source_image_url,
        user_prompt=user_prompt,
        output_format=output_format,
    )
    api_key = settings.openai_api_key.strip()
    log_row = create_ai_media_image_job(
        db,
        row=row,
        user_id=user_id,
        team_id=team_id,
        connection_id=connection_id,
        source_image_url=source_image_url,
        user_prompt=prompt,
        reference=reference,
        output_format=safe_output_format,
        size=size,
    )

    started = time.perf_counter()
    try:
        log_row.status = AiGenerationStatus.running.value
        db.commit()
        timeout_seconds = max(float(settings.ai_timeout_seconds), 300.0)
        with httpx.Client(timeout=timeout_seconds) as client:
            image_bytes, mime_type, file_name = _load_image_for_edit(client, source_image_url)
            edit_prompt = _build_media_edit_prompt(product_name=row.name, user_prompt=prompt, reference=reference)
            response = client.post(
                "https://api.openai.com/v1/images/edits",
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "model": settings.ai_image_model,
                    "prompt": edit_prompt,
                    "size": size or "1024x1024",
                    "output_format": safe_output_format,
                },
                files={"image": (file_name, image_bytes, mime_type)},
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response_payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text[:2000]}
        if response.status_code >= 400:
            message = str(_as_record(response_payload.get("error")).get("message") or "OpenAI image request failed")
            request_id = response.headers.get("x-request-id")
            if request_id:
                message = f"{message} (OpenAI request id: {request_id})"
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                response_payload=response_payload,
                error_message=message,
                latency_ms=latency_ms,
            )
            db.commit()
            raise RuntimeError(message)

        image_url, revised_prompt = _extract_generated_image(response_payload, output_format=safe_output_format)
        asset_url = _persist_generated_image(image_url, log_id=log_row.id, output_format=safe_output_format)
        usage = _usage_from_response(response_payload)
        usage["model"] = str(response_payload.get("model") or settings.ai_image_model)
        finish_ai_generation_log(
            db,
            log_row,
            status=AiGenerationStatus.success.value,
            response_payload={
                "openai_created": response_payload.get("created"),
                "revised_prompt": revised_prompt,
                "image_url": asset_url,
            },
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            cached_input_tokens=usage["cached_input_tokens"],
            reasoning_tokens=usage["reasoning_tokens"],
            output_asset_count=1,
            latency_ms=latency_ms,
        )
        db.commit()
        return asset_url, revised_prompt, usage, log_row.id
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        db.rollback()
        log_row = db.get(type(log_row), log_row.id)
        if log_row is not None and log_row.status != AiGenerationStatus.success.value:
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            db.commit()
        raise


def run_ai_media_image_job(log_id: int) -> None:
    db = SessionLocal()
    started = time.perf_counter()
    try:
        log_row = db.get(AiGenerationLog, log_id)
        if log_row is None:
            return
        if log_row.status == AiGenerationStatus.success.value:
            return
        request_payload = _as_record(log_row.request)
        row = db.get(MarketplaceProduct, log_row.product_row_id) if log_row.product_row_id else None
        if row is None:
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                error_message="Product not found for AI media job",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            db.commit()
            return

        prompt, safe_output_format = _validate_ai_media_image_request(
            source_image_url=str(request_payload.get("source_image_url") or ""),
            user_prompt=str(request_payload.get("prompt") or ""),
            output_format=str(request_payload.get("output_format") or "png"),
        )
        api_key = settings.openai_api_key.strip()
        log_row.status = AiGenerationStatus.running.value
        db.commit()

        timeout_seconds = max(float(settings.ai_timeout_seconds), 300.0)
        with httpx.Client(timeout=timeout_seconds) as client:
            image_bytes, mime_type, file_name = _load_image_for_edit(client, str(request_payload.get("source_image_url") or ""))
            edit_prompt = _build_media_edit_prompt(product_name=row.name, user_prompt=prompt, reference=_as_record(request_payload.get("reference")))
            response = client.post(
                "https://api.openai.com/v1/images/edits",
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "model": settings.ai_image_model,
                    "prompt": edit_prompt,
                    "size": str(request_payload.get("size") or "1024x1024"),
                    "output_format": safe_output_format,
                },
                files={"image": (file_name, image_bytes, mime_type)},
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response_payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text[:2000]}
        if response.status_code >= 400:
            message = str(_as_record(response_payload.get("error")).get("message") or "OpenAI image request failed")
            request_id = response.headers.get("x-request-id")
            if request_id:
                message = f"{message} (OpenAI request id: {request_id})"
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                response_payload=response_payload,
                error_message=message,
                latency_ms=latency_ms,
            )
            db.commit()
            return

        image_url, revised_prompt = _extract_generated_image(response_payload, output_format=safe_output_format)
        asset_url = _persist_generated_image(image_url, log_id=log_row.id, output_format=safe_output_format)
        usage = _usage_from_response(response_payload)
        finish_ai_generation_log(
            db,
            log_row,
            status=AiGenerationStatus.success.value,
            response_payload={
                "openai_created": response_payload.get("created"),
                "revised_prompt": revised_prompt,
                "image_url": asset_url,
            },
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            cached_input_tokens=usage["cached_input_tokens"],
            reasoning_tokens=usage["reasoning_tokens"],
            output_asset_count=1,
            latency_ms=latency_ms,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        log_row = db.get(AiGenerationLog, log_id)
        if log_row is not None and log_row.status != AiGenerationStatus.success.value:
            finish_ai_generation_log(
                db,
                log_row,
                status=AiGenerationStatus.failed.value,
                error_message=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            db.commit()
    finally:
        db.close()
