# WOzYm - AI платформа продаж Phase 1: Auth + Client Cabinet

## Ports

- `frontend`: `http://127.0.0.1:4412`
- `backend`: `http://127.0.0.1:8617`
- `postgres`: `127.0.0.1:56432`
- `mailpit smtp`: `127.0.0.1:11125`
- `mailpit ui`: `http://127.0.0.1:18125`

## Environment

1. Copy `.env.example` to `.env` in repo root.
2. Values already point to non-standard local ports.

## Infrastructure

```powershell
cd backend
python run.py infra-up
python run.py status
```

## Backend

```powershell
cd backend
pip install -r requirements.txt
python run.py migrate
python run.py
```

Checks:

- `GET http://127.0.0.1:8617/health`
- Mailpit UI `http://127.0.0.1:18125`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## API scope (phase 1)

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/refresh`
- `POST /auth/verify-email`
- `POST /auth/resend-email`
- `POST /auth/verify-phone`
- `POST /auth/resend-phone`
- `GET /me`
- `PATCH /me`
- `POST /me/password`
- `GET /me/sessions`
- `DELETE /me/sessions/{session_id}`
- `POST /messengers/link/start` (TODO stub)
- `POST /messengers/link/complete` (TODO stub)
- `POST /agent/chat` (TODO stub)

## Tests

Backend:

```powershell
cd backend
pytest -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run typecheck
npm test
```

## Graphify (project graph)

Generate актуальный граф проекта (frontend/shared/backend):

```powershell
cd D:\Projects\WOzYm - AI платформа продаж
npm run graphify
```

Auto-refresh on file changes:

```powershell
cd D:\Projects\WOzYm - AI платформа продаж
npm run graphify:watch
```

Artifacts:

- `docs/project-graph.md`
- `docs/project-graph.mmd`
- `docs/project-graph.index.json`

`quick_commit.ps1` запускает `graphify` автоматически перед `git add`.

## Smoke scenario

1. Register with `email + phone + password` from `/register`.
2. Login with email or phone from `/login`.
3. Open `/account` and verify profile/sessions load.
4. Verify phone on `/verify-phone` using code from backend logs.
5. Change password on `/account/password` and login with new password.

