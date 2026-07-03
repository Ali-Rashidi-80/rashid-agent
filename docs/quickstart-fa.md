# Rashid Agent v2 — Quickstart (feature/rashid-agent-v2)

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js — فاز ۲) + Docker (Postgres + Redis).

## پیش‌نیاز

- Python 3.11+
- Docker Desktop
- PowerShell (Windows)

## راه‌اندازی سریع

```powershell
# 1. میرورها (ایران)
.\scripts\setup-mirrors.ps1

# 2. زیرساخت
.\scripts\infra-up.ps1

# 3. وابستگی‌ها
pip install -e ".[dev]"

# 4. مهاجرت DB (وقتی Postgres بالا است)
.\scripts\migrate.ps1

# 5. API توسعه
.\scripts\dev.ps1
```

- Health: http://127.0.0.1:8000/api/v1/health
- تنظیم مسیر پروژه: `POST /api/v1/project/path` با `{"path":"D:/your/project"}`
- پیش‌نمایش ویرایش: `POST /api/v1/edits/preview`

کپی `.env.example` به `.env` و کلید Metis را پر کنید.

## تست

```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```

---
