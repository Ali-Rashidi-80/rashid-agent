# زیرساخت — Rashid Agent

[English](infrastructure.md) | **فارسی**

## پیش‌نیاز

- Docker Desktop (یا Docker Engine)
- Python 3.11+ (برای hybrid host)
- Node 20+ (برای hybrid frontend)
- PowerShell (اسکریپت‌های Windows)

## حالت‌ها

### ۱) Hybrid (پیش‌فرض توسعه)

```powershell
.\scripts\setup-mirrors.ps1
.\scripts\infra-up.ps1          # postgres + redis
.\scripts\migrate.ps1
.\scripts\dev.ps1               # API روی host
.\scripts\smoke-worker.ps1 start
```

| سرویس | پورت | تصویر / فرایند |
|--------|------|----------------|
| PostgreSQL + pgvector | `127.0.0.1:5432` | Chabokan mirror `pgvector/pgvector:pg16` |
| App DB role | `rashid_app` | RLS روی جداول KB |
| Redis | `127.0.0.1:6380` | `redis:7-alpine` via mirror |
| API | `127.0.0.1:8000` | uvicorn روی host |
| Worker | — | `arq worker.settings.WorkerSettings` |
| Web | `127.0.0.1:3000` | `npm run dev` |

### ۲) Full stack در Docker

```powershell
.\scripts\stack-up.ps1
```

سرویس‌ها: `postgres` `redis` `migrate` `api` `worker` `web` — جزئیات [deployment.fa.md](./deployment.fa.md).

### ۳) Chabokan raw / local mirror

- `.\scripts\chabokan-stack-up.ps1` → `rashid-chabokan-*`
- `.\scripts\local-mirror-up.ps1` → `rashid-mirror-*`

## Health

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

انتظار: `postgres` / `redis` / `worker` وضعیت `ok` (با worker در حال اجرا).

## حجم‌ها و داده

- Compose volumes: `pgdata` / `redisdata` (یا نام‌های chabokan/mirror)
- فایل‌های KB و runtime: `backend/data/` (gitignored؛ `.gitkeep` نگه داشته می‌شود)
- رمزها فقط در `.env` / `.env.local-mirror`

## میرورها

[mirrors-iran-fa.md](./mirrors-iran-fa.md) · [EN](./mirrors-iran.md) — PyPI، npm، Docker Engine `daemon.json`.
