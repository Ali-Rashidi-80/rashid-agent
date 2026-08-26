# Infrastructure — Rashid Agent

**English** | [فارسی](infrastructure.fa.md)

## Prerequisites

- Docker Desktop (or Docker Engine)
- Python 3.11+ (hybrid host)
- Node 20+ (hybrid frontend)
- PowerShell (Windows scripts)

## Modes

### 1) Hybrid (default development)

```powershell
.\scripts\setup-mirrors.ps1
.\scripts\infra-up.ps1          # postgres + redis
.\scripts\migrate.ps1
.\scripts\dev.ps1               # API on host
.\scripts\smoke-worker.ps1 start
```

| Service | Port | Image / process |
|---------|------|-----------------|
| PostgreSQL + pgvector | `127.0.0.1:5432` | Chabokan mirror `pgvector/pgvector:pg16` |
| App DB role | `rashid_app` | RLS on KB tables |
| Redis | `127.0.0.1:6380` | `redis:7-alpine` via mirror |
| API | `127.0.0.1:8000` | uvicorn on host |
| Worker | — | `arq worker.settings.WorkerSettings` |
| Web | `127.0.0.1:3000` | `npm run dev` |

### 2) Full stack in Docker

```powershell
.\scripts\stack-up.ps1
```

Services: `postgres` `redis` `migrate` `api` `worker` `web` — details in [deployment.md](./deployment.md).

### 3) Chabokan raw / local mirror

- `.\scripts\chabokan-stack-up.ps1` → `rashid-chabokan-*`
- `.\scripts\local-mirror-up.ps1` → `rashid-mirror-*`

## Health

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

Expect `postgres` / `redis` / `worker` status `ok` (with worker running).

## Volumes and data

- Compose volumes: `pgdata` / `redisdata` (or chabokan/mirror names)
- KB and runtime files: `backend/data/` (gitignored; `.gitkeep` kept)
- Secrets only in `.env` / `.env.local-mirror`

## Mirrors

[mirrors-iran.md](./mirrors-iran.md) — PyPI, npm, Docker Engine `daemon.json`.
