# زیرساخت — Rashid Agent

## پیش‌نیاز

- Docker Desktop
- Python 3.11+
- PowerShell

## راه‌اندازی

```powershell
.\scripts\setup.ps1
.\scripts\infra-up.ps1
.\scripts\dev.ps1
```

## سرویس‌ها

| سرویس | پورت | تصویر |
|--------|------|--------|
| PostgreSQL | 127.0.0.1:5432 | postgres:16-alpine |
| Redis | 127.0.0.1:6380 | redis:7-alpine |
| API | 127.0.0.1:8000 | uvicorn (host dev) |

## Health

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

## Worker (فاز ۱.۳+)

```bash
cd backend
arq worker.settings.WorkerSettings
```

## Hybrid dev

- Postgres + Redis در Docker
- API روی host با `--reload` (پیش‌فرض `dev.ps1`)
