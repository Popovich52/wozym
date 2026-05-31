# Phase 1 Implementation Plan: Auth + User Cabinet

Дата: 2026-05-29

## Execution Status (updated: 2026-05-30)

- [x] Root scaffolding (`backend`, `frontend`, `shared`, `.env.example`, `docker-compose.yml`, `README.md`, root `package.json` workspaces)
- [x] Non-standard ports wired (`4412`, `8617`, `56432`, `11125`, `18125`)
- [x] FastAPI scaffold + `/health` + CORS + `python run.py`
- [x] DB migrations layer (Alembic configured + initial migration created)
- [x] Auth security baseline (Argon2id, JWT access, refresh cookie, refresh token hash, route guard)
- [x] Auth API (`register/login/logout/refresh/verify/resend`)
- [x] User cabinet API (`/me`, `/me/password`, `/me/sessions`)
- [x] Email verification via SMTP (Mailpit) + phone verification codes (dev logs)
- [x] Frontend pages (`/register`, `/login`, `/verify-email`, `/verify-phone`, `/account`, `/account/password`)
- [x] Light orange UI baseline (Page UI style direction adapted, `#ff6a00` theme tokens)
- [x] Telegram/MAX architecture placeholders (`/messengers/link/start`, `/messengers/link/complete`, account block)
- [x] LangChain agent foundation placeholder (`POST /agent/chat`)
- [x] Tests: backend `pytest` green, frontend `lint/typecheck/vitest` green

## 1. Цель первого шага

Собрать первый рабочий контур продукта:

- регистрация по `email | phone + password`;
- вход по `email | phone + password`;
- подтверждение email;
- подготовка телефонной верификации через код;
- личный кабинет пользователя;
- смена пароля из ЛК;
- светлый UI на базе Page UI с основным ярко-оранжевым цветом;
- раздельный frontend/backend на нестандартных портах;
- база для дальнейшего подключения аналитики, мессенджеров Telegram/MAX и агентного слоя LangChain.

Первый шаг не включает полноценную аналитику WB/Ozon, но структура проекта должна сразу учитывать будущие модули подключений, sync jobs, уведомлений и agent service.

## 2. Базовые архитектурные решения

### Стек

- Monorepo: `npm workspaces`.
- Frontend: `Next.js + TypeScript + Tailwind CSS`.
- UI: Page UI как база визуального языка и готовых блоков.
- Backend: `FastAPI + Python`.
- DB: `PostgreSQL`.
- ORM/migrations: `SQLAlchemy + Alembic` или `SQLModel + Alembic`.
- Cache/queues later: `Redis`.
- Auth: собственный session/JWT контур на backend.
- Password hashing: `Argon2id`.
- Email delivery local: Mailpit.
- Phone verification MVP: код сохраняется в БД и логируется в dev; позже подключается SMS provider.

### Нестандартные порты

- Frontend: `4412`.
- Backend API: `8617`.
- PostgreSQL: `56432`.
- Mailpit SMTP: `11125`.
- Mailpit UI: `18125`.
- Redis later: `56379`.

### UI-направление

- Светлый фон.
- Основной акцент: ярко-оранжевый.
- Рекомендуемый primary color: `#ff6a00`.
- Secondary colors: graphite/neutral для текста и линий.
- Не делать маркетинговый лендинг первым экраном.
- Первый экран после входа: рабочий личный кабинет.
- Формы должны быть компактными, понятными, без декоративного шума.

## 3. Структура проекта

```text
WOzYm - AI платформа продаж/
  package.json
  docker-compose.yml
  .env.example
  README.md
  apps/
    web/
      package.json
      next.config.ts
      tailwind.config.ts
      postcss.config.js
      src/
        app/
          layout.tsx
          page.tsx
          login/
            page.tsx
          register/
            page.tsx
          verify-email/
            page.tsx
          verify-phone/
            page.tsx
          account/
            page.tsx
          account/
            password/
              page.tsx
        components/
          auth/
          account/
          layout/
          ui/
        lib/
          api.ts
          auth.ts
          validation.ts
        styles/
          globals.css
    api/
      pyproject.toml
      app/
        main.py
        core/
          config.py
          security.py
          database.py
        modules/
          auth/
            router.py
            service.py
            schemas.py
            models.py
          users/
            router.py
            service.py
            schemas.py
            models.py
          notifications/
            models.py
          audit/
            models.py
        tests/
          test_auth.py
          test_users.py
      alembic/
  packages/
    shared/
      src/
        auth-contracts.ts
        user-contracts.ts
```

## 4. Backend: модели данных

### `users`

Поля:

- `id`
- `email`
- `phone`
- `password_hash`
- `name`
- `email_verified_at`
- `phone_verified_at`
- `status`: `active | blocked | deleted`
- `created_at`
- `updated_at`

Ограничения:

- `email` unique, nullable false.
- `phone` unique, nullable false.
- password never returned by API.

### `email_verification_tokens`

Поля:

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

### `phone_verification_codes`

Поля:

- `id`
- `user_id`
- `code_hash`
- `expires_at`
- `attempts`
- `used_at`
- `created_at`

### `sessions`

Поля:

- `id`
- `user_id`
- `refresh_token_hash`
- `user_agent`
- `ip_address`
- `expires_at`
- `revoked_at`
- `created_at`

### `audit_events`

Поля:

- `id`
- `user_id`
- `action`
- `metadata`
- `ip_address`
- `created_at`

События первого шага:

- `auth.register`
- `auth.login`
- `auth.logout`
- `auth.email_verified`
- `auth.phone_verified`
- `user.password_changed`

## 5. Backend: API первого шага

### Auth

- `POST /auth/register`
  - input: `email`, `phone`, `password`, `name?`
  - creates user, email token, phone code
  - returns safe user profile and auth state

- `POST /auth/login`
  - input: `login`, `password`
  - `login` accepts email or phone
  - returns access token and sets refresh token cookie

- `POST /auth/logout`
  - revokes current session

- `POST /auth/refresh`
  - rotates access token

- `POST /auth/verify-email`
  - input: `token`
  - marks email as verified

- `POST /auth/resend-email`
  - sends new verification email

- `POST /auth/verify-phone`
  - input: `code`
  - marks phone as verified

- `POST /auth/resend-phone`
  - creates new phone code

### User Cabinet

- `GET /me`
  - returns current user profile

- `PATCH /me`
  - updates `name`, later profile settings

- `POST /me/password`
  - input: `current_password`, `new_password`
  - validates current password
  - updates hash
  - revokes other sessions

- `GET /me/sessions`
  - returns active sessions

- `DELETE /me/sessions/{session_id}`
  - revokes session

## 6. Frontend: страницы и UX

### `/register`

Форма:

- name
- email
- phone
- password
- password confirmation

Поведение:

- client validation через `zod`;
- inline ошибки;
- после успеха переход на экран подтверждения;
- телефон нормализуется до E.164 на backend.

### `/login`

Форма:

- email или phone
- password

Поведение:

- один input `login`;
- backend сам определяет email/phone;
- после входа переход в `/account`.

### `/verify-email`

Состояния:

- token accepted;
- token expired;
- token already used;
- resend email.

### `/verify-phone`

Форма:

- 6-digit code.

Dev режим:

- код можно увидеть в backend logs.

Production later:

- SMS provider adapter.

### `/account`

Блоки:

- профиль;
- email status;
- phone status;
- security status;
- linked messengers placeholder: Telegram/MAX;
- account activity;
- shortcut to change password.

### `/account/password`

Форма:

- current password;
- new password;
- confirm new password.

Поведение:

- после смены пароля показывается success state;
- остальные сессии отзываются.

## 7. Page UI и визуальная база

Использование Page UI:

- брать как основу композиции и компонентов для auth/account shell;
- адаптировать под продуктовый кабинет, не под лендинг;
- использовать Tailwind tokens и CSS variables;
- primary accent: `#ff6a00`;
- focus ring: orange;
- buttons: orange primary, neutral secondary;
- фон: `#f8fafc` или близкий светлый neutral;
- cards: radius не больше `8px`;
- плотная компоновка для ЛК.

Tailwind tokens:

```ts
colors: {
  mp: {
    orange: '#ff6a00',
    orangeHover: '#e85f00',
    ink: '#171717',
    muted: '#6b7280',
    line: '#e5e7eb',
    surface: '#ffffff',
    background: '#f8fafc',
  }
}
```

## 8. Запуск проекта

### Инфраструктура

```powershell
docker compose up -d
```

Поднимает:

- PostgreSQL: `localhost:56432`
- Mailpit SMTP: `localhost:11125`
- Mailpit UI: `http://localhost:18125`

### Backend

```powershell
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8617 --reload
```

Health:

```text
http://127.0.0.1:8617/health
```

### Frontend

```powershell
cd apps/web
npm install
npm run dev
```

App:

```text
http://127.0.0.1:4412
```

## 9. `.env.example`

```dotenv
APP_ENV=development

WEB_URL=http://127.0.0.1:4412
API_URL=http://127.0.0.1:8617

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=56432
POSTGRES_DB=wozym
POSTGRES_USER=wozym
POSTGRES_PASSWORD=wozym
DATABASE_URL=postgresql+asyncpg://wozym:wozym@127.0.0.1:56432/wozym

JWT_ACCESS_SECRET=replace-local-access-secret
JWT_REFRESH_SECRET=replace-local-refresh-secret
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=30

SMTP_HOST=127.0.0.1
SMTP_PORT=11125
SMTP_FROM=no-reply@local.wozym

PHONE_VERIFICATION_DEV_MODE=true
PASSWORD_HASH_ALGORITHM=argon2id
```

## 10. Тестирование

Backend tests:

- register creates user;
- duplicate email rejected;
- duplicate phone rejected;
- login by email works;
- login by phone works;
- wrong password rejected;
- email verification works;
- phone verification works;
- password change requires current password;
- password change revokes other sessions.

Frontend tests:

- register form validation;
- login form validation;
- account page protected;
- change password success and error states.

Smoke checks:

- `GET /health` returns ok;
- register -> email appears in Mailpit;
- phone code appears in dev logs;
- login -> `/account`;
- password change -> old password rejected, new password works.

## 11. Acceptance criteria

Первый шаг готов, если:

- frontend работает на `4412`;
- backend работает на `8617`;
- PostgreSQL работает на `56432`;
- регистрация принимает email + phone + password;
- пользователь может войти по email + password;
- пользователь может войти по phone + password;
- email verification работает через Mailpit;
- phone verification работает в dev mode;
- `/account` доступен только после входа;
- в ЛК виден профиль пользователя;
- пользователь может сменить пароль;
- структура проекта готова для следующих модулей: Telegram/MAX, marketplace connections, analytics, LangChain agent service.

## 12. Следующий шаг после этого плана

После утверждения первого шага нужно:

1. Сгенерировать monorepo.
2. Поднять `docker-compose.yml`.
3. Реализовать backend auth module.
4. Реализовать frontend auth/account pages на Page UI/Tailwind.
5. Прогнать smoke-сценарий регистрации и входа.

