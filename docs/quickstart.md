# Rashid Agent — Quickstart

**English** | [فارسی](quickstart-fa.md)

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js) + Docker (Postgres/pgvector + Redis).

## Prerequisites

- Python 3.11+
- Node 20+
- Docker Desktop
- PowerShell (Windows scripts)

## Hybrid setup (recommended for development)

```powershell
# 1. Mirrors (Iran / Chabokan)
.\scripts\setup-mirrors.ps1

# 2. Env files
copy .env.example .env
copy frontend\.env.example frontend\.env.local
# Fill METIS_API_KEY, SECRETS_ENCRYPTION_KEY, TENANT_SEED_*

# 3. Infra
.\scripts\infra-up.ps1

# 4. Dependencies
pip install -e ".[dev]"

# 5. DB migrate
.\scripts\migrate.ps1

# 6. API
.\scripts\dev.ps1
```

Frontend (separate terminal):

```powershell
cd frontend
npm install
npm run dev
```

Worker (separate terminal — large KB / queued Telegram):

```powershell
.\scripts\smoke-worker.ps1 start
```

- Health: http://127.0.0.1:8000/api/v1/health
- UI: http://127.0.0.1:3000
- After tenant login: `/knowledge` and `/bots`
- Platform guide: [multi-tenant.md](./multi-tenant.md)

## Full stack in Docker

```powershell
.\scripts\stack-up.ps1
```

Chabokan / mirror deploy: [deployment.md](./deployment.md)

## Tests

```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```
