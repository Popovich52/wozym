---
marp: true
title: WOzYm - AI платформа продаж-like Analytics Platform Architecture
description: Reference analysis and scalable architecture proposal
theme: default
paginate: true
size: 16:9
---

# WOzYm - AI платформа продаж-like Analytics Platform

## Анализ референса, архитектура и Phase 1

Дата: 2026-05-29  
Основной референс: `https://wiki.wozym.io`

---

# Цель продукта

Построить SaaS-кабинет для селлеров маркетплейсов, где пользователь:

- регистрируется и управляет личным кабинетом
- подключает кабинеты WB/Ozon через API-ключи
- получает внутреннюю аналитику продаж, остатков, расходов и прибыли
- видит качество данных, историю загрузок и сверку с отчетами маркетплейса
- получает оперативные уведомления через Telegram или MAX
- использует агентный слой для анализа, рекомендаций и автоматизации

---

# Что делает WOzYm - AI платформа продаж по референсу

WOzYm - AI платформа продаж позиционируется как платформа аналитики маркетплейсов:

- анализ конкурентов и ниш
- внутренняя аналитика кабинета продавца
- внешняя и внутренняя реклама
- SEO и карточки товаров
- автоматизация рутины
- AI-инструменты и ассистенты

Источник: `wiki.wozym.io`

---

# Ключевой вывод из референса

Для первого этапа важнее не внешний маркетинговый сайт, а рабочий продуктовый контур:

- профиль клиента
- команда и доступы
- подключения WB/Ozon
- загрузка данных
- себестоимость
- сверка
- аналитическая сводка
- история запросов и выгрузок
- уведомления

---

# Профиль и личный кабинет

В профиле WOzYm - AI платформа продаж есть:

- счета и аккаунт
- подключения
- команда и доступы
- партнерская программа
- история запросов
- уведомления
- удаление аккаунта

Источник: `wiki.wozym.io/ru/Профиль_WOzYm - AI платформа продаж`

---

# Аккаунт: базовая модель

В аккаунте референса хранятся:

- имя
- email
- телефон
- язык отчетов
- API-токен аккаунта
- бонусные дни
- подписка и счета
- доступ к подключенным сотрудникам

Для нас это ядро Phase 1: identity + account + organization.

---

# Команды и доступы

Референс поддерживает совместную работу по подписке.

В нашей архитектуре это означает:

- `User` не равен `Account`
- `Organization` или `Tenant` владеет данными
- `Membership` задает роль пользователя
- подключения принадлежат организации
- права на подключения могут быть отдельными от прав на аккаунт

---

# История запросов и выгрузок

В WOzYm - AI платформа продаж пользователь видит:

- историю запросов отчетов
- историю скачанных файлов
- статусы выгрузок: формируется, готов, ошибка, удален
- автора запроса
- период отчета
- повторный доступ к файлам ограниченное время

Это важный паттерн для всех тяжелых отчетов.

---

# Подключения как центральный объект

Подключение является источником данных и границей доступа.

Минимальная модель:

- marketplace: `WB | OZON`
- type: seller cabinet, ads, price, reviews, etc.
- status: draft, active, error, disabled
- credentials encrypted
- sync state
- owner organization
- access policy
- audit trail

---

# Кабинет WB: функциональный контур

По референсу Кабинет WB покрывает:

- расчет поставки с учетом оборачиваемости
- продажи, выкупы и возвраты
- маржинальность и рентабельность
- ABC-анализ
- товары
- сводку
- еженедельные отчеты
- загрузку себестоимости и параметров
- карточку товара
- AI-ассистента выбора склада

Источник: `wiki.wozym.io/ru/Личный_кабинет`

---

# Подключение WB

Референс требует токен с категориями доступа:

- статистика
- аналитика
- контент
- маркетплейс
- продвижение
- поставки
- финансы

Важно: старый токен лучше обновлять, а не создавать новое подключение, чтобы не терять историю и настройки.

---

# Данные WB и сверка

Для WB важны:

- еженедельные отчеты как ключевой источник финансовых данных
- учет по кассовому методу для части отчетов
- учет по методу начисления для других отчетов
- сверка с отчетами Wildberries
- явное объяснение расхождений

Архитектурный вывод: нужна модель `data_lineage` и расчетные версии метрик.

---

# Кабинет Ozon: функциональный контур

По референсу Кабинет Ozon покрывает:

- сумму продаж и составляющие
- расходы магазина и детализацию
- прибыль
- маржинальность
- рентабельность
- сводку
- товары
- операционные расходы
- загрузку себестоимости

Источник: `wiki.wozym.io/ru/Кабинет_Ozon`

---

# Ozon: Сводка

Сводка Ozon показывает:

- продажи
- возвраты
- комиссии
- логистику
- услуги агентов
- компенсации
- продвижение
- налоги
- хранение и приемку
- себестоимость
- прочие расходы
- прибыль, маржинальность, ROS

---

# Ozon: Товары

Отчет по товарам включает:

- подключение и выбор нескольких подключений
- дату последнего обновления
- ограничение обновления: не чаще одного раза в час
- статусы товаров
- период анализа до 180 дней
- фильтры по остаткам, марже, ROS, оборачиваемости, ABC, убыточности
- поиск, таблицу SKU и экспорт

---

# Базовая продуктовая карта

Модули первой линии:

- ЛК клиента
- Организация и роли
- Marketplace Connections
- Sync Center
- Data Quality & Reconciliation
- Seller Analytics
- Exports
- Notifications
- Agent Layer
- Billing позже, но модель должна быть заложена

---

# Архитектурный принцип

Начинать лучше с модульного монолита, но с границами будущих сервисов.

Почему:

- меньше инфраструктурной сложности на старте
- быстрее выпуск MVP
- проще держать транзакционную целостность
- модули можно отделить позже без переписывания домена

Границы сервисов сразу проектируются через модули, события и контракты.

---

# Предлагаемый стек

Frontend:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- TanStack Table
- Recharts или Apache ECharts

Backend:

- Python FastAPI или NestJS
- PostgreSQL
- Redis
- очередь: RabbitMQ, Redis Streams или NATS
- worker: Celery, Dramatiq, Temporal или BullMQ

---

# Хранилища данных

OLTP:

- PostgreSQL: пользователи, аккаунты, подключения, роли, настройки

Analytics:

- ClickHouse или PostgreSQL partitions на старте
- отдельные fact-таблицы по заказам, продажам, остаткам, расходам

Files:

- S3-compatible object storage для экспортов и импортов

Cache:

- Redis для сессий, rate limits, locks, short-lived state

---

# Главные доменные сущности

- `User`
- `IdentityCredential`
- `PhoneVerification`
- `Organization`
- `Membership`
- `MarketplaceConnection`
- `MarketplaceCredential`
- `SyncJob`
- `SyncRunLog`
- `Product`
- `Order`
- `Sale`
- `StockSnapshot`
- `Expense`
- `CostPrice`
- `MetricSnapshot`
- `ExportJob`
- `NotificationChannel`
- `AgentConversation`

---

# Phase 1: ЛК клиента

Регистрация:

- email
- телефон
- пароль
- подтверждение email
- подтверждение телефона через код
- согласие с офертой и обработкой данных

После регистрации:

- создается личная организация
- пользователь становится владельцем
- открывается onboarding подключения WB/Ozon

---

# Phase 1: Привязка мессенджера

Поддержать два канала:

- Telegram
- MAX

Единая модель:

- `NotificationProvider`
- `NotificationChannel`
- `MessengerAccountLink`
- `WebhookEvent`
- `DeliveryAttempt`

Технически оба канала должны подключаться как provider adapters.

---

# Telegram / MAX: сценарий привязки

1. Пользователь выбирает канал в ЛК
2. Система генерирует одноразовый link-token
3. Пользователь открывает бота
4. Бот получает token или code
5. Backend связывает messenger user id с аккаунтом
6. Пользователь выбирает типы уведомлений

События:

- sync completed
- sync failed
- token expired
- low stock
- negative margin
- export ready
- agent recommendation

---

# Auth и безопасность

Нужно заложить сразу:

- Argon2id или bcrypt для паролей
- email verification
- phone verification
- optional 2FA позже
- session rotation
- device/session list
- encrypted marketplace credentials
- audit log
- rate limits
- IP/device anomaly flags
- scoped access tokens for internal services

---

# Интеграция с WB/Ozon

Adapter pattern:

- `MarketplaceAdapter`
- `WBAdapter`
- `OzonAdapter`
- `MockAdapter`

Интерфейсы:

- `validateCredentials`
- `fetchProducts`
- `fetchOrders`
- `fetchSales`
- `fetchStocks`
- `fetchExpenses`
- `fetchAds`
- `fetchReports`

Все входящие данные нормализуются до внутренней канонической схемы.

---

# Pipeline загрузки данных

1. Credential validation
2. Sync job created
3. Connector fetch
4. Raw payload persisted
5. Normalize
6. Validate
7. Upsert facts
8. Recalculate metric snapshots
9. Reconciliation check
10. Notify user

Raw data хранить обязательно: это основа дебага, сверки и повторной обработки.

---

# Аналитическая модель

Факты:

- orders
- sales
- returns
- stocks
- products
- promotions
- expenses
- commissions
- logistics
- cost prices

Слои:

- raw
- normalized
- facts
- metric snapshots
- materialized reports

---

# Метрики первого релиза

Сводка:

- выручка
- заказы
- продажи
- возвраты
- комиссии
- логистика
- операционные расходы
- себестоимость
- прибыль
- маржинальность
- ROS
- остатки
- проблемные SKU

Товары:

- прибыль по SKU
- маржа
- оборачиваемость
- дни до out-of-stock
- ABC
- убыточные товары
- товары без себестоимости

---

# Agent Layer: зачем он нужен

Агентный слой не должен напрямую менять данные без контроля.

Он должен:

- объяснять метрики
- находить причины падения прибыли
- отвечать на вопросы по данным
- предлагать действия
- формировать отчеты
- запускать безопасные read-only tools
- создавать задачи для пользователя
- отправлять уведомления через TG/MAX

---

# LangChain / LangGraph контур

Рекомендуемая схема:

- отдельный `agent-service`
- LangChain tools поверх внутренних API
- LangGraph для управляемых workflow
- RAG по базе знаний и внутренним документам
- memory per organization/user
- policy layer перед tool execution
- tracing и evaluation

LangChain дает готовую архитектуру агентов и инструменты для model/tool orchestration.

---

# Agent Tools первого этапа

Read-only tools:

- `get_kpis`
- `get_profit_by_day`
- `get_products_profitability`
- `get_low_stock_skus`
- `get_negative_margin_skus`
- `get_sync_status`
- `get_connection_health`

Action tools с подтверждением:

- `send_report_to_messenger`
- `create_export`
- `schedule_sync`
- `create_user_task`

---

# Масштабирование

Вертикальный путь:

- PostgreSQL partitions
- batch workers
- Redis locks
- материализованные отчеты

Горизонтальный путь:

- connector service
- sync orchestration service
- analytics service
- notification service
- agent service
- export service

Переход к сервисам делать по нагрузке, а не заранее.

---

# Observability

Обязательные метрики:

- sync duration
- sync failures by provider
- API latency
- report query latency
- queue depth
- webhook delivery failures
- auth failures
- agent tool calls
- cost per agent conversation

Логи:

- structured JSON
- correlation id
- organization id
- connection id
- sync job id

---

# Phase 1 Scope

Входит:

- регистрация email + телефон + пароль
- подтверждение email
- подтверждение телефона
- организация по умолчанию
- профиль пользователя
- привязка Telegram или MAX
- Marketplace Connections shell
- WB/Ozon mock connectors
- dashboard MVP
- sync jobs
- cost prices
- reconciliation MVP
- agent-service skeleton

---

# Phase 1 не включает

Не включать в первый этап:

- биллинг
- сложные тарифы
- полноценную внешнюю аналитику конкурентов
- управление рекламой
- репрайсер
- автоответы
- production-grade real-time ingestion всех API
- write-actions агентом без ручного подтверждения

Это снижает риск и ускоряет первый рабочий релиз.

---

# Phase 1 UX flow

1. Регистрация
2. Подтверждение email
3. Подтверждение телефона
4. Создание организации
5. Привязка TG/MAX
6. Создание подключения WB/Ozon
7. Проверка ключей
8. Первый sync
9. Загрузка себестоимости
10. Сверка
11. Сводка
12. Рекомендации агента

---

# Рекомендуемая структура репозитория

```text
apps/
  web/
  api/
  worker/
  agent-service/
packages/
  database/
  domain/
  connectors/
  analytics/
  notifications/
  ui/
infra/
  docker/
  migrations/
docs/
```

На старте можно держать это как monorepo.

---

# API контуры Phase 1

Auth:

- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/verify-phone`
- `POST /auth/login`

Profile:

- `GET /me`
- `PATCH /me`
- `GET /me/sessions`

Messenger:

- `POST /messengers/link`
- `POST /webhooks/telegram`
- `POST /webhooks/max`

---

# Analytics API Phase 1

Connections:

- `GET /connections`
- `POST /connections`
- `POST /connections/{id}/test`
- `POST /connections/{id}/sync`

Reports:

- `GET /analytics/summary`
- `GET /analytics/products`
- `GET /analytics/stocks`
- `GET /analytics/profit/daily`
- `GET /analytics/reconciliation`
- `POST /exports`

Agent:

- `POST /agent/chat`
- `GET /agent/conversations`

---

# Данные и приватность

Критичные решения:

- credentials шифровать отдельно от основной БД
- ключи маркетплейсов не возвращать во frontend
- raw API payload хранить с ограниченным доступом
- audit log на все действия с подключениями
- messenger id считать персональными данными
- телефон хранить нормализованно в E.164
- все отчеты фильтровать по `organization_id`

---

# Главные риски

- разные методы учета у маркетплейсов
- расхождения в данных между API и отчетами
- rate limits WB/Ozon
- нестабильность внешних API
- стоимость агентных запросов
- безопасность marketplace credentials
- поддержка нескольких организаций и сотрудников
- сложность объяснения метрик пользователю

---

# MVP acceptance criteria

MVP считается рабочим, если пользователь может:

- зарегистрироваться с email, телефоном и паролем
- подтвердить email и телефон
- привязать Telegram или MAX
- добавить mock WB/Ozon подключение
- запустить sync
- загрузить себестоимость
- увидеть сводку и товары
- получить уведомление о sync result
- задать агенту вопрос по своим данным

---

# План реализации

Неделя 1:

- auth, профиль, organization, migrations
- email/phone verification
- UI shell

Неделя 2:

- messenger linking
- connections
- sync jobs
- mock WB/Ozon adapters

Неделя 3:

- analytics schema
- dashboard MVP
- cost prices
- reconciliation

Неделя 4:

- agent-service skeleton
- LangChain tools
- notifications
- hardening

---

# Источники

- `https://wiki.wozym.io/`
- `https://wiki.wozym.io/ru/Профиль_WOzYm - AI платформа продаж`
- `https://wiki.wozym.io/ru/Личный_кабинет`
- `https://wiki.wozym.io/ru/Кабинет_Ozon`
- `https://wiki.wozym.io/ru/Кабинет_Ozon/Сводка`
- `https://wiki.wozym.io/ru/Кабинет_Ozon/Товары`
- `https://wiki.wozym.io/Личный_кабинет/Подключения`
- `https://wiki.wozym.io/ru/FAQ/История_запросов`
- `https://docs.langchain.com/oss/python/langchain/overview`
- `https://core.telegram.org/bots/api`

---

# Следующее действие

Начать Phase 1 с нуля:

- создать monorepo
- поднять `web`, `api`, `worker`, `agent-service`
- добавить PostgreSQL, Redis, миграции
- реализовать регистрацию email + phone + password
- добавить профиль и привязку Telegram/MAX
- заложить модель подключений и sync jobs

