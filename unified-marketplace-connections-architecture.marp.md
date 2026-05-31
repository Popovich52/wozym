---
marp: true
title: Unified Marketplace Connections Architecture
description: WB, Ozon, Yandex Market connection and data architecture
theme: default
paginate: true
size: 16:9
---

# Unified Marketplace Connections

## WB, Ozon, Yandex Market

Дата: 2026-05-30  
Цель: единая архитектура подключений, токенов, синхронизаций и данных

---

# Задача

Поддержать несколько маркетплейсов без переписывания ядра:

- у пользователя или команды может быть несколько подключений
- одно подключение может иметь несколько credentials/контуров
- данные должны быть трассируемы до токена и конкретного API-запроса
- аналитика должна строиться в единой модели
- детали API не должны теряться

---

# Общий вывод

## Делать унифицированную архитектуру

Едиными должны быть:

- подключения и права доступа
- credentials и ротация токенов
- sync jobs, cursors, raw API events
- нормализованные витрины аналитики

Разными остаются:

- provider-specific поля credentials
- детали API-ответов
- часть справочников и финансовых сущностей

---

# Различия авторизации

| Provider | Auth | Особенности |
|---|---|---|
| WB | `Authorization` token | категории токена, срок около 180 дней |
| Ozon Seller | `Client-Id` + `Api-Key` | ключ с ролью, срок около 6 месяцев |
| Ozon Performance | `client_id` + `client_secret` -> `Bearer` | отдельный рекламный контур |
| Yandex Market | `Api-Key` | OAuth устаревший, важны `businessId` и `campaignId` |

---

# Унифицированная модель подключения

```text
marketplace_connections
- id
- team_id
- owner_user_id
- provider: WB | OZON | YANDEX_MARKET
- name
- status: DRAFT | ACTIVE | ERROR | DISABLED
- external_account_id
- external_account_name
- created_by_user_id
- updated_by_user_id
- created_at
- updated_at
```

Подключение = логический источник данных и граница доступа.

---

# Credentials как отдельная сущность

```text
marketplace_connection_credentials
- id
- connection_id
- provider
- credential_kind
- auth_scheme
- client_id_plain
- api_key_plain
- client_secret_plain
- oauth_token_plain
- refresh_token_plain
- scopes_json
- token_meta_json
- expires_at
- is_primary
- is_active
```

Один `connection_id` может иметь несколько credentials.

---

# Примеры credential_kind

## WB
- `WB_CONTENT`
- `WB_ANALYTICS`
- `WB_STATISTICS`
- `WB_PRICES`
- `WB_PROMOTION`
- `WB_FINANCE`

## Ozon
- `OZON_SELLER`
- `OZON_PERFORMANCE`

## Yandex Market
- `YM_API_KEY`
- `YM_OAUTH_LEGACY`

---

# Управление доступом

```text
marketplace_connection_acl
- id
- connection_id
- team_member_id
- can_read
- can_sync
- can_manage
- can_view_secret
- created_by_user_id
- updated_by_user_id
```

`can_view_secret` нужно отделить от `can_manage`: менеджер может запускать синхронизацию без доступа к токену.

---

# Единый sync-контур

```text
marketplace_sync_jobs
- id
- connection_id
- credential_id
- provider
- domain: PRODUCTS | PRICES | STOCKS | ORDERS | RETURNS | FINANCE | ADS
- period_from
- period_to
- status
- requested_by_user_id
- created_at
```

```text
marketplace_sync_runs
- id
- job_id
- connection_id
- credential_id
- status
- started_at
- finished_at
- api_calls_count
- error_message
```

---

# Raw слой обязателен

```text
marketplace_raw_api_events
- id
- run_id
- connection_id
- credential_id
- provider
- endpoint
- http_method
- request_json
- response_status
- response_json
- fetched_at
```

Зачем:

- воспроизводимость расчетов
- аудит источника данных
- отладка расхождений
- поддержка новых витрин без повторной загрузки

---

# Единые витрины аналитики

```text
marketplace_products
marketplace_prices_daily
marketplace_stocks_daily
marketplace_orders
marketplace_order_items
marketplace_returns
marketplace_finance_transactions
marketplace_ad_campaigns
marketplace_ad_stats_daily
```

Обязательные поля:

- `provider`
- `connection_id`
- `external_id`
- `business_date` или `event_at`
- `source_run_id`
- `raw_event_id`

---

# Provider-specific слой

## WB
- `wb_token_capabilities`
- `wb_realization_reports`
- `wb_ad_campaign_details`
- `wb_search_query_stats`

## Ozon
- `ozon_seller_products_ext`
- `ozon_performance_reports`
- `ozon_finance_operations_ext`

## Yandex Market
- `ym_businesses`
- `ym_campaigns`
- `ym_order_status_history`
- `ym_quality_index_snapshots`

---

# Почему нельзя только общие таблицы

Одинаковые названия не означают одинаковую семантику:

- `campaignId` в Yandex Market часто означает магазин
- Ozon имеет отдельный Performance API для рекламы
- WB дробит доступы по категориям токена
- финансовые операции у WB/Ozon/Yandex имеют разные модели начисления
- статусы заказов и возвратов не совпадают один к одному

Поэтому: общие витрины для отчетов, provider-specific таблицы для точности.

---

# Оптимальная архитектура

```text
UI / API
  -> Connection Service
  -> Credential Service
  -> Sync Orchestrator
  -> Provider Adapters
      - WBAdapter
      - OzonSellerAdapter
      - OzonPerformanceAdapter
      - YandexMarketAdapter
  -> Raw Store
  -> Normalizers
  -> Analytics Marts
```

Адаптеры знают API. Остальная система работает с едиными contracts.

---

# Правила хранения секретов

## Базовая рекомендация
- хранить секреты шифрованно
- в UI показывать маску
- аудит каждого просмотра секрета
- хранить историю ротаций
- alert до истечения токена

## Если нужен открытый вид
- отдельный флаг `storage_mode = PLAIN`
- доступ только через `can_view_secret`
- запись в audit log при каждом чтении
- запрет массового экспорта секретов

---

# Проверка подключений

## WB
- проверка `/ping`
- проверка соответствия категории токена нужному API

## Ozon
- Seller: `/v1/roles`
- Performance: token endpoint и тестовый запрос по кампаниям

## Yandex Market
- `GET /v2/campaigns`
- проверка доступности `businessId` и `campaignId`

---

# Порядок реализации

1. Расширить `Marketplace` значением `YANDEX_MARKET`.
2. Добавить общую таблицу credentials.
3. Добавить sync runs, cursors, raw events.
4. Сделать provider adapter interface.
5. Первым адаптером реализовать Ozon Seller + Performance.
6. Затем WB и Yandex Market по той же модели.
7. Нормализованные витрины строить после raw-загрузки.

---

# Итог

Оптимальная модель: единое ядро подключений + разные адаптеры.

Это дает:

- масштабирование на новые маркетплейсы
- единую систему прав и аудита
- трассировку данных до токена
- гибкость при изменениях API
- общие аналитические отчеты без потери деталей источника

---

# Источники

- `https://dev.wildberries.ru/docs/openapi/api-information`
- `https://dev.wildberries.ru/en/openapi/api-information?locale=ru`
- `https://yandex.ru/dev/market/partner-api/doc/ru/concepts/authorization`
- `https://yandex.ru/dev/market/partner-api/doc/ru/concepts/access`
- `https://docs.ozon.com/global/api/intro/`
- `https://docs.ozon.com/global/api/perfomance-api/`
- `https://docs.ozon.com/api/seller/swagger.json`
- `https://docs.ozon.com/api/performance/swagger.json`
