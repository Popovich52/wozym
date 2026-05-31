# Phase 1 Checklist: Auth + User Cabinet

Дата создания: 2026-05-30

Статусы:

- `[ ]` не начато
- `[~]` в работе
- `[x]` сделано

## Execution Snapshot (updated: 2026-05-30)

- [x] Базовый каркас проекта и порты
- [x] Рабочие backend/frontend раннеры (`backend\python run.py`, `frontend\npm run dev`)
- [x] Реализован backend auth + cabinet API
- [x] Реализована email/phone verification механика
- [x] Реализован frontend auth + account + password flow
- [x] Пройдены backend и frontend тесты
- [x] Alembic-миграции (конфиг + initial migration добавлены)

## 0. Подготовка проекта

- [ ] Создать monorepo в `D:\Projects\WOzYm - AI платформа продаж`.
- [ ] Добавить root `package.json` с workspaces.
- [ ] Создать структуру `apps/web`.
- [ ] Создать структуру `apps/api`.
- [ ] Создать структуру `packages/shared`.
- [ ] Добавить root `.env.example`.
- [ ] Добавить root `README.md`.
- [ ] Добавить `.gitignore`.
- [ ] Добавить `docker-compose.yml`.

Критерий приемки:

- [ ] В корне проекта есть базовая структура monorepo.
- [ ] `npm install` в корне проекта не падает.
- [ ] Все базовые конфиги лежат в ожидаемых местах.

## 1. Нестандартные порты и инфраструктура

- [ ] Настроить PostgreSQL на `localhost:56432`.
- [ ] Настроить Mailpit SMTP на `localhost:11125`.
- [ ] Настроить Mailpit UI на `http://localhost:18125`.
- [ ] Зарезервировать frontend порт `4412`.
- [ ] Зарезервировать backend port `8617`.
- [ ] Подготовить порт Redis later: `56379`.
- [ ] Добавить healthcheck для PostgreSQL в `docker-compose.yml`.
- [ ] Добавить команды запуска инфраструктуры в `README.md`.

Критерий приемки:

- [ ] `docker compose up -d` поднимает PostgreSQL и Mailpit.
- [ ] `http://localhost:18125` открывает Mailpit UI.
- [ ] PostgreSQL доступен на `localhost:56432`.

## 2. Backend scaffold

- [ ] Создать FastAPI-приложение в `apps/api`.
- [ ] Добавить `pyproject.toml`.
- [ ] Добавить `app/main.py`.
- [ ] Добавить `GET /health`.
- [ ] Добавить модуль `core/config.py`.
- [ ] Добавить модуль `core/database.py`.
- [ ] Добавить модуль `core/security.py`.
- [ ] Подключить CORS для frontend `http://127.0.0.1:4412`.
- [ ] Настроить запуск backend на `127.0.0.1:8617`.

Критерий приемки:

- [ ] `uv run uvicorn app.main:app --host 127.0.0.1 --port 8617 --reload` запускает backend.
- [ ] `http://127.0.0.1:8617/health` возвращает `ok`.

## 3. Backend database и миграции

- [ ] Подключить SQLAlchemy или SQLModel.
- [ ] Подключить Alembic.
- [ ] Создать первую миграцию.
- [ ] Добавить модель `User`.
- [ ] Добавить модель `EmailVerificationToken`.
- [ ] Добавить модель `PhoneVerificationCode`.
- [ ] Добавить модель `Session`.
- [ ] Добавить модель `AuditEvent`.
- [ ] Добавить unique index на `users.email`.
- [ ] Добавить unique index на `users.phone`.
- [ ] Добавить timestamps `created_at`, `updated_at`.

Критерий приемки:

- [ ] `alembic upgrade head` применяет миграции без ошибок.
- [ ] Таблицы создаются в PostgreSQL.
- [ ] Повторный запуск миграций не ломает схему.

## 4. Backend security

- [ ] Подключить Argon2id для password hashing.
- [ ] Добавить password policy.
- [ ] Добавить генерацию access token.
- [ ] Добавить refresh token cookie.
- [ ] Добавить hash refresh token перед сохранением.
- [ ] Добавить session rotation.
- [ ] Добавить logout с отзывом текущей сессии.
- [ ] Добавить защиту authenticated routes.
- [ ] Добавить rate-limit TODO для auth endpoints.

Критерий приемки:

- [ ] Пароль никогда не хранится в открытом виде.
- [ ] Refresh token хранится только в виде hash.
- [ ] Защищенные endpoints недоступны без авторизации.

## 5. Backend auth API

- [ ] Добавить `POST /auth/register`.
- [ ] Добавить `POST /auth/login`.
- [ ] Добавить вход по email.
- [ ] Добавить вход по телефону.
- [ ] Добавить `POST /auth/logout`.
- [ ] Добавить `POST /auth/refresh`.
- [ ] Добавить `POST /auth/verify-email`.
- [ ] Добавить `POST /auth/resend-email`.
- [ ] Добавить `POST /auth/verify-phone`.
- [ ] Добавить `POST /auth/resend-phone`.
- [ ] Добавить нормализацию телефона до E.164.
- [ ] Добавить validation errors в едином формате.

Критерий приемки:

- [ ] Пользователь может зарегистрироваться с email + phone + password.
- [ ] Пользователь может войти по email + password.
- [ ] Пользователь может войти по phone + password.
- [ ] Неверный пароль возвращает `401`.
- [ ] Duplicate email возвращает понятную ошибку.
- [ ] Duplicate phone возвращает понятную ошибку.

## 6. Backend email verification

- [ ] Подключить SMTP-конфиг для Mailpit.
- [ ] Генерировать email verification token при регистрации.
- [ ] Хранить hash token в БД.
- [ ] Отправлять письмо в Mailpit.
- [ ] Реализовать verify endpoint.
- [ ] Реализовать resend endpoint.
- [ ] Обрабатывать expired token.
- [ ] Обрабатывать already used token.

Критерий приемки:

- [ ] После регистрации письмо попадает в Mailpit.
- [ ] Email можно подтвердить по token.
- [ ] Повторное использование token не подтверждает email повторно.

## 7. Backend phone verification

- [ ] Генерировать 6-digit phone code.
- [ ] Хранить hash code в БД.
- [ ] Добавить TTL для code.
- [ ] Добавить attempts counter.
- [ ] Добавить dev-mode вывод code в backend logs.
- [ ] Реализовать verify endpoint.
- [ ] Реализовать resend endpoint.
- [ ] Подготовить adapter interface для будущего SMS provider.

Критерий приемки:

- [ ] После регистрации создается phone verification code.
- [ ] В dev mode code можно увидеть в backend logs.
- [ ] Phone можно подтвердить кодом.
- [ ] Неверный code увеличивает attempts.
- [ ] Expired code не принимается.

## 8. Backend user cabinet API

- [ ] Добавить `GET /me`.
- [ ] Добавить `PATCH /me`.
- [ ] Добавить `POST /me/password`.
- [ ] Добавить `GET /me/sessions`.
- [ ] Добавить `DELETE /me/sessions/{session_id}`.
- [ ] Добавить revoke other sessions после смены пароля.
- [ ] Добавить audit event `user.password_changed`.

Критерий приемки:

- [ ] `/me` возвращает текущего пользователя.
- [ ] `/me` не возвращает password hash.
- [ ] Пользователь может сменить пароль.
- [ ] Старый пароль перестает работать после смены.
- [ ] Другие сессии отзываются после смены пароля.

## 9. Frontend scaffold

- [ ] Создать Next.js app в `apps/web`.
- [ ] Настроить TypeScript.
- [ ] Настроить Tailwind CSS.
- [ ] Настроить запуск на `127.0.0.1:4412`.
- [ ] Подключить Page UI как дизайн-основу.
- [ ] Добавить CSS variables для темы.
- [ ] Настроить bright orange primary color `#ff6a00`.
- [ ] Добавить API client в `src/lib/api.ts`.
- [ ] Добавить auth state handling.
- [ ] Добавить protected route handling.

Критерий приемки:

- [ ] `npm run dev` запускает frontend на `4412`.
- [ ] Светлая тема применяется по умолчанию.
- [ ] Primary buttons используют bright orange.
- [ ] Frontend умеет обращаться к backend на `8617`.

## 10. Frontend auth pages

- [ ] Добавить страницу `/register`.
- [ ] Добавить форму name/email/phone/password/confirm password.
- [ ] Добавить client validation через zod.
- [ ] Добавить страницу `/login`.
- [ ] Добавить единый login input для email или phone.
- [ ] Добавить password input.
- [ ] Добавить обработку ошибок backend.
- [ ] Добавить redirect на `/account` после успешного входа.
- [ ] Добавить loading states.
- [ ] Добавить disabled states на submit.

Критерий приемки:

- [ ] Пользователь может заполнить регистрацию.
- [ ] Ошибки формы показываются рядом с полями.
- [ ] Пользователь может войти по email.
- [ ] Пользователь может войти по phone.
- [ ] После входа открывается `/account`.

## 11. Frontend verification pages

- [ ] Добавить страницу `/verify-email`.
- [ ] Добавить state success для email verification.
- [ ] Добавить state expired для email verification.
- [ ] Добавить кнопку resend email.
- [ ] Добавить страницу `/verify-phone`.
- [ ] Добавить 6-digit code input.
- [ ] Добавить resend phone code.
- [ ] Добавить success state для phone verification.
- [ ] Добавить error state для неверного code.

Критерий приемки:

- [ ] Email verification можно пройти из ссылки письма.
- [ ] Phone verification можно пройти через code.
- [ ] Resend действия работают из UI.

## 12. Frontend личный кабинет

- [ ] Добавить страницу `/account`.
- [ ] Показать имя пользователя.
- [ ] Показать email.
- [ ] Показать phone.
- [ ] Показать статус email verification.
- [ ] Показать статус phone verification.
- [ ] Добавить placeholder блока Telegram/MAX.
- [ ] Добавить ссылку на `/account/password`.
- [ ] Добавить список активных сессий.
- [ ] Добавить logout.

Критерий приемки:

- [ ] `/account` доступен только авторизованному пользователю.
- [ ] Неавторизованный пользователь попадает на `/login`.
- [ ] В ЛК видны email/phone verification statuses.
- [ ] Logout завершает сессию.

## 13. Frontend смена пароля

- [ ] Добавить страницу `/account/password`.
- [ ] Добавить поле current password.
- [ ] Добавить поле new password.
- [ ] Добавить поле confirm new password.
- [ ] Добавить client validation.
- [ ] Добавить success state.
- [ ] Добавить error state для неверного current password.
- [ ] После смены пароля обновлять auth state.

Критерий приемки:

- [ ] Пользователь может сменить пароль.
- [ ] При неверном текущем пароле показывается ошибка.
- [ ] После смены старый пароль не работает.
- [ ] Новый пароль работает для входа.

## 14. Messenger foundation для Telegram/MAX

- [ ] Добавить backend модели `NotificationChannel`.
- [ ] Добавить backend модели `MessengerAccountLink`.
- [ ] Добавить enum provider: `telegram | max`.
- [ ] Добавить placeholder UI в `/account`.
- [ ] Подготовить `POST /messengers/link/start`.
- [ ] Подготовить `POST /messengers/link/complete`.
- [ ] Добавить TODO для Telegram webhook.
- [ ] Добавить TODO для MAX webhook.

Критерий приемки:

- [ ] В архитектуре есть место для Telegram/MAX.
- [ ] В ЛК виден блок привязки мессенджеров.
- [ ] Реальная привязка может быть добавлена без переделки auth.

## 15. Agent layer foundation для LangChain

- [ ] Создать заготовку `apps/agent-service` или описать ее в структуре.
- [ ] Добавить shared auth contract для будущих tool calls.
- [ ] Добавить TODO API `POST /agent/chat`.
- [ ] Добавить TODO для read-only tools.
- [ ] Добавить TODO для audit agent actions.

Критерий приемки:

- [ ] Структура проекта не блокирует добавление LangChain service.
- [ ] Auth/session модель пригодна для agent tool authorization.

## 16. Документация запуска

- [ ] Описать запуск инфраструктуры.
- [ ] Описать запуск backend.
- [ ] Описать запуск frontend.
- [ ] Описать env variables.
- [ ] Описать smoke сценарий.
- [ ] Описать порты.

Критерий приемки:

- [ ] Новый разработчик может поднять проект по README.
- [ ] Все команды запуска работают на Windows PowerShell.

## 17. Тесты

- [ ] Добавить backend test для registration.
- [ ] Добавить backend test для duplicate email.
- [ ] Добавить backend test для duplicate phone.
- [ ] Добавить backend test для login by email.
- [ ] Добавить backend test для login by phone.
- [ ] Добавить backend test для wrong password.
- [ ] Добавить backend test для email verification.
- [ ] Добавить backend test для phone verification.
- [ ] Добавить backend test для password change.
- [ ] Добавить frontend test для register validation.
- [ ] Добавить frontend test для login validation.
- [ ] Добавить frontend test для account protected state.
- [ ] Добавить frontend test для password change form.

Критерий приемки:

- [ ] Backend tests проходят.
- [ ] Frontend tests проходят.
- [ ] Typecheck проходит.
- [ ] Lint проходит.

## 18. Финальная smoke-проверка Phase 1

- [ ] `docker compose up -d`.
- [ ] Backend запущен на `http://127.0.0.1:8617`.
- [ ] Frontend запущен на `http://127.0.0.1:4412`.
- [ ] Mailpit открыт на `http://localhost:18125`.
- [ ] Пользователь регистрируется по email + phone + password.
- [ ] Email письмо приходит в Mailpit.
- [ ] Email подтверждается.
- [ ] Phone code появляется в dev logs.
- [ ] Phone подтверждается.
- [ ] Пользователь входит по email + password.
- [ ] Пользователь входит по phone + password.
- [ ] Пользователь открывает `/account`.
- [ ] Пользователь меняет пароль.
- [ ] Пользователь входит с новым паролем.

Критерий приемки:

- [ ] Полный сценарий проходит без ручных SQL-команд.
- [ ] Нет конфликтов стандартных портов.
- [ ] Первый шаг готов к расширению на marketplace connections и аналитику.

