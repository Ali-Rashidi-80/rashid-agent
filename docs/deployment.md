# Deployment — Docker / Chabokan — Rashid Agent

**English** | [فارسی](deployment.fa.md)

## Three deployment modes

| Mode | File | Containers | Use |
|------|------|------------|-----|
| Hybrid dev | `docker-compose.yml` | `postgres` + `redis` only (default) | API/frontend on host |
| Full local | `docker-compose.yml --profile full` | + `migrate` `api` `worker` `web` | Full local stack |
| Chabokan raw | `docker-compose.chabokan.yml` | `rashid-chabokan-*` | VPS / remote raw containers |
| Local mirror (DR) | `docker-compose.local-mirror.yml` | `rashid-mirror-*` | DR clone like Liquidglass |
| Backend split | `backend/docker-compose.yml` | API (+ optional db/redis) | Panel separate from web |

## Chabokan mirrors (required for builds in Iran)

All default `FROM` / `image` values use `mirror2.chabokan.net`:

| Layer | Value |
|-------|--------|
| Python | `mirror2.chabokan.net/library/python:3.11-slim-bookworm` |
| Node | `mirror2.chabokan.net/library/node:20-alpine` |
| Postgres+pgvector | `mirror2.chabokan.net/pgvector/pgvector:pg16` |
| Redis | `mirror2.chabokan.net/library/redis:7-alpine` |
| PyPI | `https://mirror2.chabokan.net/pypi/simple/` |
| npm | `https://mirror2.chabokan.net/npm/` |
| Debian apt | `https://mirror2.chabokan.net/debian` |

Host setup: `.\scripts\setup-mirrors.ps1` and [mirrors-iran.md](./mirrors-iran.md).  
If a tag is missing on the mirror, set e.g. `POSTGRES_IMAGE=pgvector/pgvector:pg16` in `.env` (with `daemon.json` registry mirrors).

## Quick start — full local stack

```powershell
copy .env.example .env
# Fill secrets in `.env` (*.example files intentionally leave secrets empty)
.\scripts\setup-mirrors.ps1
.\scripts\stack-up.ps1
```

- Web: http://127.0.0.1:3000
- API: http://127.0.0.1:8000/api/v1/health

## Quick start — Chabokan / remote raw containers

```powershell
copy .env.example .env
# POSTGRES_PASSWORD and SECRETS_ENCRYPTION_KEY required
.\scripts\chabokan-stack-up.ps1
```

Or:

```bash
DOCKER_BUILDKIT=1 docker compose -f docker-compose.chabokan.yml --env-file .env build
docker compose -f docker-compose.chabokan.yml --env-file .env up -d
```

Containers:

- `rashid-chabokan-postgres`
- `rashid-chabokan-redis`
- `rashid-chabokan-api`
- `rashid-chabokan-worker`
- `rashid-chabokan-web`
- `rashid-chabokan-migrate` (once)

For TLS and a public domain, put a reverse proxy (Nginx/Caddy) in front of `web`/`api`.  
Telegram webhook: `https://<HOST>/api/v1/integrations/telegram/webhook/<integration_id>` — see [telegram.md](./telegram.md).

## Local mirror (mirror containers)

Naming pattern like Liquidglass (`lg-mirror-*`) → here `rashid-mirror-*`:

```powershell
copy .env.local-mirror.example .env.local-mirror
# Change LOCAL_DB_PASSWORD and REDIS_PASSWORD
.\scripts\local-mirror-up.ps1
```

| Container | Role |
|-----------|------|
| `rashid-mirror-db` | Postgres + pgvector |
| `rashid-mirror-redis` | Redis with password |
| `rashid-mirror-api` | FastAPI |
| `rashid-mirror-worker` | ARQ |
| `rashid-mirror-web` | Next.js |

Default local ports: API `8001`, Web `3001`, DB `5433`, Redis `6381` (bound to `127.0.0.1` only).

## Split deploy (web / API) on Chabokan panel

Variable checklist: `.env.chabokan.split.example`  
Point `DATABASE_URL` / `REDIS_URL` at Chabokan-managed DB/Redis; no in-compose `db` service required.

```bash
# API (+ worker) only with backend image
cd backend
docker compose --env-file ../.env up -d api worker
# For DB/Redis in the same file: --profile with-db
```

Frontend: build `frontend/Dockerfile` with `BACKEND_URL=https://api.YOUR_DOMAIN`.

## Critical production variables

| Variable | Why |
|----------|-----|
| `SECRETS_ENCRYPTION_KEY` | Encrypt bot tokens in DB |
| `POSTGRES_PASSWORD` | DB |
| `METIS_API_KEY` | LLM + embeddings |
| `TENANT_SEED_ADMIN_*` | First tenant admin (adl-omid) |
| `RASHID_TOKEN` | Optional; global API lock |
| `TELEGRAM_*` | Dev/seed only; prefer Integrations API |
| `SMS_CONSOLE_API_TOKEN` / `SMS_PROVIDER_MODE` | MeliPayamak OTP (pattern `477732`); local usually `stub` |
| Docker build | `DOCKER_BUILDKIT=1` — pip layer + cache mount |

Frontend host: `frontend/.env.example` → `.env.local`.

## Health

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:3000/fa
```

Health should report `postgres` / `redis` / `worker` as `ok` when the worker is up.

## Migrate

The `migrate` container (or `backend/start.sh` entrypoint) runs `alembic upgrade head` before `api`.  
Skip migrate on one service with `RASHID_SKIP_MIGRATE=1`.

## Env templates (no secrets)

| File | Role |
|------|------|
| `.env.example` | Root / backend template |
| `backend/.env.example` | Reminder to load root `.env` |
| `frontend/.env.example` | Next.js host |
| `.env.local-mirror.example` | DR mirror |
| `.env.chabokan.split.example` | Chabokan panel checklist |

Sensitive fields in examples stay **empty**.

## Live test of all containers

Creates a temporary env (gitignored), builds/ups both stacks, checks health + login:

```powershell
python scripts/live_docker_stack_test.py
```

Default test ports (avoid hybrid clashes): API `28000` / Web `23000` (chabokan) and API `8001` / Web `3001` (mirror).  
Non-secret summary: `backend/data/live_docker_stack_note.txt`
