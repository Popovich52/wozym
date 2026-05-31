from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import (
    MarketplaceConnection,
    MarketplaceConnectionCredential,
    MarketplaceProduct,
    MarketplaceRawApiEvent,
    MarketplaceSyncCursor,
    MarketplaceSyncRun,
    SyncDomain,
    SyncJobStatus,
)


@dataclass
class ProductSnapshot:
    external_product_id: str | None
    external_offer_id: str | None
    external_sku: str | None
    barcode: str | None
    name: str | None
    brand: str | None
    category_name: str | None
    status: str | None
    image_urls: list[str]
    video_urls: list[str]
    payload: dict[str, Any]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _safe_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return None


def _collect_urls(payload: Any, image_urls: set[str], video_urls: set[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_lower = str(key).lower()
            url_value = _safe_url(value)
            if url_value:
                if "video" in key_lower:
                    video_urls.add(url_value)
                elif any(part in key_lower for part in ("image", "img", "photo", "picture", "preview")):
                    image_urls.add(url_value)
            _collect_urls(value, image_urls, video_urls)
        return
    if isinstance(payload, list):
        for value in payload:
            url_value = _safe_url(value)
            if url_value:
                image_urls.add(url_value)
            _collect_urls(value, image_urls, video_urls)


def _extract_media(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    image_urls: set[str] = set()
    video_urls: set[str] = set()
    _collect_urls(payload, image_urls, video_urls)
    return sorted(image_urls)[:40], sorted(video_urls)[:20]


def _chunks(values: list[Any], size: int) -> list[list[Any]]:
    if size <= 0:
        return [values]
    return [values[i : i + size] for i in range(0, len(values), size)]


def _select_active_credential(db: Session, connection: MarketplaceConnection) -> MarketplaceConnectionCredential | None:
    return (
        db.query(MarketplaceConnectionCredential)
        .filter(MarketplaceConnectionCredential.connection_id == connection.id)
        .filter(MarketplaceConnectionCredential.is_active.is_(True))
        .order_by(MarketplaceConnectionCredential.is_primary.desc(), MarketplaceConnectionCredential.id.asc())
        .first()
    )


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_raw_event(
    db: Session,
    *,
    run: MarketplaceSyncRun,
    credential_id: int | None,
    endpoint: str,
    http_method: str,
    request_payload: dict[str, Any] | None,
    response_status: int | None,
    response_payload: dict[str, Any] | list[Any] | None,
) -> MarketplaceRawApiEvent:
    event = MarketplaceRawApiEvent(
        run_id=run.id,
        connection_id=run.connection_id,
        credential_id=credential_id,
        provider=run.provider,
        endpoint=endpoint,
        http_method=http_method,
        request=request_payload if isinstance(request_payload, dict) else None,
        response_status=response_status,
        response=response_payload if isinstance(response_payload, dict) else {"items": response_payload or []},
        fetched_at=_now(),
    )
    db.add(event)
    db.flush()
    return event


def _save_cursor(
    db: Session,
    *,
    connection_id: int,
    credential_id: int | None,
    provider: str,
    cursor_key: str,
    cursor_value: str | None,
) -> None:
    row = (
        db.query(MarketplaceSyncCursor)
        .filter(MarketplaceSyncCursor.connection_id == connection_id)
        .filter(MarketplaceSyncCursor.credential_id == credential_id)
        .filter(MarketplaceSyncCursor.provider == provider)
        .filter(MarketplaceSyncCursor.domain == SyncDomain.products.value)
        .filter(MarketplaceSyncCursor.cursor_key == cursor_key)
        .first()
    )
    now = _now()
    if row is None:
        row = MarketplaceSyncCursor(
            connection_id=connection_id,
            credential_id=credential_id,
            provider=provider,
            domain=SyncDomain.products.value,
            cursor_key=cursor_key,
            cursor_value=cursor_value,
            last_synced_at=now,
            updated_at=now,
        )
        db.add(row)
        return
    row.cursor_value = cursor_value
    row.last_synced_at = now
    row.updated_at = now


def _persist_products(
    db: Session,
    *,
    connection: MarketplaceConnection,
    run: MarketplaceSyncRun,
    raw_event_id: int | None,
    products: list[ProductSnapshot],
) -> int:
    now = _now()
    current_rows = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.connection_id == connection.id)
        .filter(MarketplaceProduct.provider == connection.provider)
        .filter(MarketplaceProduct.is_current.is_(True))
        .all()
    )
    by_key: dict[tuple[str, str], MarketplaceProduct] = {}
    for row in current_rows:
        key = (
            (row.external_product_id or "").strip(),
            (row.external_offer_id or row.external_sku or "").strip(),
        )
        by_key[key] = row

    seen_keys: set[tuple[str, str]] = set()
    changed_rows = 0
    for item in products:
        key = (
            (item.external_product_id or "").strip(),
            (item.external_offer_id or item.external_sku or "").strip(),
        )
        if key == ("", ""):
            continue
        seen_keys.add(key)
        existing = by_key.get(key)
        if existing is not None:
            same = (
                existing.external_sku == item.external_sku
                and existing.barcode == item.barcode
                and existing.name == item.name
                and existing.brand == item.brand
                and existing.category_name == item.category_name
                and existing.status == item.status
                and (existing.image_urls or []) == item.image_urls
                and (existing.video_urls or []) == item.video_urls
            )
            if same:
                existing.updated_at = now
                continue
            existing.is_current = False
            existing.valid_to = now

        db.add(
            MarketplaceProduct(
                connection_id=connection.id,
                provider=connection.provider,
                external_product_id=item.external_product_id,
                external_offer_id=item.external_offer_id,
                external_sku=item.external_sku,
                barcode=item.barcode,
                name=item.name,
                brand=item.brand,
                category_name=item.category_name,
                status=item.status,
                image_urls=item.image_urls,
                video_urls=item.video_urls,
                payload=item.payload,
                source_run_id=run.id,
                raw_event_id=raw_event_id,
                valid_from=now,
                valid_to=None,
                is_current=True,
            )
        )
        changed_rows += 1

    for key, existing in by_key.items():
        if key not in seen_keys:
            existing.is_current = False
            existing.valid_to = now

    return changed_rows


def _sync_ozon_products(
    db: Session,
    *,
    run: MarketplaceSyncRun,
    credential: MarketplaceConnectionCredential,
    health_only: bool,
) -> tuple[list[ProductSnapshot], int]:
    if not credential.client_id_plain or not credential.api_key_plain:
        raise ValueError("Для Ozon Seller нужны Client ID и Api Key.")
    headers = {
        "Client-Id": credential.client_id_plain.strip(),
        "Api-Key": credential.api_key_plain.strip(),
        "Content-Type": "application/json",
    }
    api_calls = 0
    with httpx.Client(timeout=15.0) as client:
        if health_only:
            response = client.post("https://api-seller.ozon.ru/v4/product/info/limit", headers=headers, json={})
            payload = _json_or_empty(response)
            _write_raw_event(
                db,
                run=run,
                credential_id=credential.id,
                endpoint="/v4/product/info/limit",
                http_method="POST",
                request_payload={},
                response_status=response.status_code,
                response_payload=payload if isinstance(payload, dict) else {},
            )
            api_calls += 1
            if response.status_code != 200:
                raise ValueError("Ozon Seller API недоступен или ключ невалидный.")
            return [], api_calls

        # Step 1: fetch full product id list with pagination.
        list_items: list[dict[str, Any]] = []
        last_id = ""
        while True:
            request_payload = {"filter": {"visibility": "ALL"}, "last_id": last_id, "limit": 1000}
            response = client.post("https://api-seller.ozon.ru/v3/product/list", headers=headers, json=request_payload)
            payload = _json_or_empty(response)
            _write_raw_event(
                db,
                run=run,
                credential_id=credential.id,
                endpoint="/v3/product/list",
                http_method="POST",
                request_payload=request_payload,
                response_status=response.status_code,
                response_payload=payload if isinstance(payload, dict) else {},
            )
            api_calls += 1
            if response.status_code != 200:
                raise ValueError("Не удалось получить список товаров Ozon.")

            result = payload.get("result") if isinstance(payload, dict) else {}
            items = result.get("items") if isinstance(result, dict) else []
            if not isinstance(items, list):
                items = []
            list_items.extend([item for item in items if isinstance(item, dict)])

            next_last_id = result.get("last_id") if isinstance(result, dict) else None
            next_last_id_str = str(next_last_id or "")
            if not items or not next_last_id_str or next_last_id_str == last_id:
                break
            last_id = next_last_id_str

        product_ids = []
        list_item_by_pid: dict[str, dict[str, Any]] = {}
        for item in list_items:
            pid_raw = item.get("product_id") or item.get("id")
            pid = str(pid_raw or "").strip()
            if not pid:
                continue
            product_ids.append(pid_raw)
            list_item_by_pid[pid] = item

        if not product_ids:
            return [], api_calls

        # Step 2: fetch detailed product cards (name, barcodes, statuses, images, prices, stocks, etc.).
        info_by_pid: dict[str, dict[str, Any]] = {}
        for batch in _chunks(product_ids, 100):
            details_payload = {"product_id": batch}
            response = client.post("https://api-seller.ozon.ru/v3/product/info/list", headers=headers, json=details_payload)
            payload = _json_or_empty(response)
            _write_raw_event(
                db,
                run=run,
                credential_id=credential.id,
                endpoint="/v3/product/info/list",
                http_method="POST",
                request_payload=details_payload,
                response_status=response.status_code,
                response_payload=payload if isinstance(payload, dict) else {},
            )
            api_calls += 1
            if response.status_code != 200:
                raise ValueError("Не удалось получить детальную информацию по товарам Ozon.")
            info_items = payload.get("items") if isinstance(payload, dict) else []
            if not isinstance(info_items, list):
                info_items = []
            for info_item in info_items:
                if not isinstance(info_item, dict):
                    continue
                pid = str(info_item.get("id") or "").strip()
                if pid:
                    info_by_pid[pid] = info_item

        # Step 3: fetch attributes (contains extended attributes and frequently video links).
        attrs_by_pid: dict[str, dict[str, Any]] = {}
        for batch in _chunks(product_ids, 100):
            attr_payload = {
                "filter": {"product_id": batch, "visibility": "ALL"},
                "limit": max(len(batch), 1),
                "sort_dir": "ASC",
            }
            response = client.post("https://api-seller.ozon.ru/v4/product/info/attributes", headers=headers, json=attr_payload)
            payload = _json_or_empty(response)
            _write_raw_event(
                db,
                run=run,
                credential_id=credential.id,
                endpoint="/v4/product/info/attributes",
                http_method="POST",
                request_payload=attr_payload,
                response_status=response.status_code,
                response_payload=payload if isinstance(payload, dict) else {},
            )
            api_calls += 1
            if response.status_code != 200:
                raise ValueError("Не удалось получить атрибуты товаров Ozon.")
            attr_items = payload.get("result") if isinstance(payload, dict) else []
            if not isinstance(attr_items, list):
                attr_items = []
            for attr_item in attr_items:
                if not isinstance(attr_item, dict):
                    continue
                pid = str(attr_item.get("id") or "").strip()
                if pid:
                    attrs_by_pid[pid] = attr_item

        snapshots: list[ProductSnapshot] = []
        for pid, list_item in list_item_by_pid.items():
            info_item = info_by_pid.get(pid, {})
            attr_item = attrs_by_pid.get(pid, {})
            payload_source = {
                "list_item": list_item,
                "info_item": info_item,
                "attributes_item": attr_item,
            }
            media_images, media_videos = _extract_media(payload_source)

            barcodes = info_item.get("barcodes") if isinstance(info_item, dict) else None
            barcode = None
            if isinstance(barcodes, list) and barcodes:
                barcode = str(barcodes[0]) if barcodes[0] is not None else None
            if not barcode and isinstance(attr_item, dict):
                barcode = str(attr_item.get("barcode") or "") or None

            status_name = None
            statuses = info_item.get("statuses") if isinstance(info_item, dict) else None
            if isinstance(statuses, dict):
                status_name = statuses.get("status_name")
            if not isinstance(status_name, str) or not status_name.strip():
                status_name = "Архив" if bool(info_item.get("is_archived") or list_item.get("archived")) else "Активен"

            brand_name = None
            attributes = attr_item.get("attributes") if isinstance(attr_item, dict) else None
            if isinstance(attributes, list):
                for attr in attributes:
                    if not isinstance(attr, dict):
                        continue
                    try:
                        attr_id = int(attr.get("id") or 0)
                    except (TypeError, ValueError):
                        attr_id = 0
                    if attr_id != 31:
                        continue
                    values = attr.get("values")
                    if isinstance(values, list) and values:
                        first = values[0]
                        if isinstance(first, dict) and isinstance(first.get("value"), str):
                            brand_name = first.get("value")
                            break

            category_name = None
            if isinstance(info_item.get("category_name"), str):
                category_name = info_item.get("category_name")
            elif isinstance(attr_item.get("description_category_id"), int):
                category_name = f"category:{attr_item.get('description_category_id')}"

            snapshots.append(
                ProductSnapshot(
                    external_product_id=pid,
                    external_offer_id=str(info_item.get("offer_id") or list_item.get("offer_id") or "") or None,
                    external_sku=str(info_item.get("sku") or "") or None,
                    barcode=barcode,
                    name=(info_item.get("name") if isinstance(info_item.get("name"), str) else None),
                    brand=brand_name,
                    category_name=category_name,
                    status=status_name,
                    image_urls=media_images,
                    video_urls=media_videos,
                    payload=payload_source,
                )
            )
        return snapshots, api_calls


def _sync_wb_products(
    db: Session,
    *,
    run: MarketplaceSyncRun,
    credential: MarketplaceConnectionCredential,
    health_only: bool,
) -> tuple[list[ProductSnapshot], int]:
    token = (credential.api_key_plain or credential.access_token_plain or "").strip()
    if not token:
        raise ValueError("Для Wildberries нужен токен API.")
    headers = {"Authorization": token, "Content-Type": "application/json"}
    request_payload = {"settings": {"cursor": {"limit": 100}, "filter": {"withPhoto": -1}}}
    with httpx.Client(timeout=15.0) as client:
        response = client.post("https://content-api.wildberries.ru/content/v2/get/cards/list", headers=headers, json=request_payload)
    payload = _json_or_empty(response)
    raw_event = _write_raw_event(
        db,
        run=run,
        credential_id=credential.id,
        endpoint="/content/v2/get/cards/list",
        http_method="POST",
        request_payload=request_payload,
        response_status=response.status_code,
        response_payload=payload if isinstance(payload, dict) else {},
    )
    if response.status_code >= 400:
        raise ValueError("Не удалось получить товары Wildberries.")
    if health_only:
        return [], 1

    cards = []
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("cards"), list):
            cards = data["cards"]
        elif isinstance(payload.get("cards"), list):
            cards = payload["cards"]

    snapshots: list[ProductSnapshot] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        media_images, media_videos = _extract_media(card)
        snapshots.append(
            ProductSnapshot(
                external_product_id=str(card.get("nmID") or card.get("imtID") or "") or None,
                external_offer_id=str(card.get("vendorCode") or "") or None,
                external_sku=str(card.get("vendorCode") or "") or None,
                barcode=None,
                name=(card.get("title") if isinstance(card.get("title"), str) else None),
                brand=(card.get("brand") if isinstance(card.get("brand"), str) else None),
                category_name=(card.get("subjectName") if isinstance(card.get("subjectName"), str) else None),
                status=(card.get("object") if isinstance(card.get("object"), str) else "ACTIVE"),
                image_urls=media_images,
                video_urls=media_videos,
                payload={"card": card, "raw_event_id": raw_event.id},
            )
        )
    return snapshots, 1


def _sync_yandex_market_products(
    db: Session,
    *,
    run: MarketplaceSyncRun,
    credential: MarketplaceConnectionCredential,
    health_only: bool,
) -> tuple[list[ProductSnapshot], int]:
    api_key = (credential.api_key_plain or credential.access_token_plain or "").strip()
    business_id = str((credential.token_meta or {}).get("business_id") or "").strip()
    if not api_key:
        raise ValueError("Для Yandex Market нужен API-ключ.")
    if not business_id:
        raise ValueError("Для Yandex Market укажите business_id в token_meta_json.")
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    with httpx.Client(timeout=20.0) as client:
        if health_only:
            response = client.get("https://api.partner.market.yandex.ru/campaigns", headers=headers)
            payload = _json_or_empty(response)
            _write_raw_event(
                db,
                run=run,
                credential_id=credential.id,
                endpoint="/campaigns",
                http_method="GET",
                request_payload=None,
                response_status=response.status_code,
                response_payload=payload if isinstance(payload, dict) else {},
            )
            if response.status_code >= 400:
                raise ValueError("Yandex Market API недоступен или ключ невалидный.")
            return [], 1

        request_payload = {"offerIds": [], "archived": False, "limit": 200}
        response = client.post(
            f"https://api.partner.market.yandex.ru/businesses/{business_id}/offer-mappings",
            headers=headers,
            json=request_payload,
        )
    payload = _json_or_empty(response)
    raw_event = _write_raw_event(
        db,
        run=run,
        credential_id=credential.id,
        endpoint=f"/businesses/{business_id}/offer-mappings",
        http_method="POST",
        request_payload=request_payload,
        response_status=response.status_code,
        response_payload=payload if isinstance(payload, dict) else {},
    )
    if response.status_code >= 400:
        raise ValueError("Не удалось получить товары Yandex Market.")

    result = payload.get("result") if isinstance(payload, dict) else {}
    offer_mappings = result.get("offerMappings") if isinstance(result, dict) else []
    if not isinstance(offer_mappings, list):
        offer_mappings = []

    snapshots: list[ProductSnapshot] = []
    for mapping in offer_mappings:
        if not isinstance(mapping, dict):
            continue
        offer = mapping.get("offer") if isinstance(mapping.get("offer"), dict) else {}
        market = mapping.get("marketSkuMapping") if isinstance(mapping.get("marketSkuMapping"), dict) else {}
        product = mapping.get("mapping") if isinstance(mapping.get("mapping"), dict) else {}
        payload_source = {"mapping": mapping, "raw_event_id": raw_event.id}
        media_images, media_videos = _extract_media(payload_source)
        snapshots.append(
            ProductSnapshot(
                external_product_id=str(product.get("marketSku") or market.get("marketSku") or "") or None,
                external_offer_id=str(offer.get("shopSku") or "") or None,
                external_sku=str(offer.get("shopSku") or "") or None,
                barcode=str(offer.get("barcode") or "") or None,
                name=(offer.get("name") if isinstance(offer.get("name"), str) else None),
                brand=(offer.get("vendor") if isinstance(offer.get("vendor"), str) else None),
                category_name=(market.get("marketCategoryName") if isinstance(market.get("marketCategoryName"), str) else None),
                status=(offer.get("availability") if isinstance(offer.get("availability"), str) else "ACTIVE"),
                image_urls=media_images,
                video_urls=media_videos,
                payload=payload_source,
            )
        )
    return snapshots, 1


def sync_products_for_connection(
    db: Session,
    *,
    connection: MarketplaceConnection,
    requested_by_user_id: int,
    dry_run: bool,
    sync_job_id: int | None = None,
) -> tuple[str, int, str | None]:
    credential = _select_active_credential(db, connection)
    if credential is None:
        return SyncJobStatus.failed.value, 0, "Нет активного ключа для синхронизации."

    run = MarketplaceSyncRun(
        sync_job_id=sync_job_id,
        connection_id=connection.id,
        credential_id=credential.id,
        provider=connection.provider,
        domain=SyncDomain.products.value,
        status=SyncJobStatus.running.value,
        started_at=_now(),
        requested_by_user_id=requested_by_user_id,
    )
    db.add(run)
    db.flush()

    processed_rows = 0
    api_calls_count = 0
    error_message: str | None = None
    now = _now()
    try:
        if connection.provider == "OZON":
            products, api_calls_count = _sync_ozon_products(db, run=run, credential=credential, health_only=dry_run)
        elif connection.provider == "WB":
            products, api_calls_count = _sync_wb_products(db, run=run, credential=credential, health_only=dry_run)
        elif connection.provider == "YANDEX_MARKET":
            products, api_calls_count = _sync_yandex_market_products(db, run=run, credential=credential, health_only=dry_run)
        else:
            raise ValueError(f"Провайдер {connection.provider} пока не поддержан.")

        credential.last_checked_at = now
        credential.last_success_at = now
        credential.last_error_at = None
        connection.last_success_at = now
        connection.last_error_at = None
        connection.last_error_message = None

        if not dry_run and products:
            raw_event_id = (
                db.query(MarketplaceRawApiEvent.id)
                .filter(MarketplaceRawApiEvent.run_id == run.id)
                .order_by(MarketplaceRawApiEvent.id.desc())
                .limit(1)
                .scalar()
            )
            processed_rows = _persist_products(
                db,
                connection=connection,
                run=run,
                raw_event_id=raw_event_id,
                products=products,
            )
            _save_cursor(
                db,
                connection_id=connection.id,
                credential_id=credential.id,
                provider=connection.provider,
                cursor_key="products_last_sync",
                cursor_value=now.isoformat(),
            )

        run.status = SyncJobStatus.success.value
        run.api_calls_count = api_calls_count
        run.processed_rows = processed_rows
        run.finished_at = _now()
        return SyncJobStatus.success.value, processed_rows, None
    except Exception as exc:
        error_message = str(exc)
        run.status = SyncJobStatus.failed.value
        run.error_message = error_message
        run.finished_at = _now()
        credential.last_checked_at = now
        credential.last_error_at = now
        connection.last_error_at = now
        connection.last_error_message = error_message[:500]
        return SyncJobStatus.failed.value, 0, error_message
    finally:
        run.finished_at = run.finished_at or _now()
