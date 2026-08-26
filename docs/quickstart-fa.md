# Rashid Agent — Quickstart (فارسی)

[English](quickstart.md) | **فارسی**

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js) + Docker (Postgres/pgvector + Redis).

## پیش‌نیاز

- Python 3.11+
- Node 20+
- Docker Desktop
- PowerShell (Windows)

## راه‌اندازی سریع (hybrid)

```powershell
# 1. میرورها (ایران / چابکان)
.\scripts\setup-mirrors.ps1

# 2. کپی env
copy .env.example .env
copy frontend\.env.example frontend\.env.local
# METIS_API_KEY و SECRETS_ENCRYPTION_KEY و TENANT_SEED_* را پر کنید

# 3. زیرساخت
.\scripts\infra-up.ps1

# 4. وابستگی‌ها
pip install -e ".[dev]"

# 5. مهاجرت DB
.\scripts\migrate.ps1

# 6. API توسعه
.\scripts\dev.ps1
```

Frontend (ترمینال جدا):

```powershell
cd frontend
npm install
npm run dev
```

Worker (ترمینال جدا، برای KB بزرگ و تلگرام صف‌شده):

```powershell
.\scripts\smoke-worker.ps1 start
```

- Health: http://127.0.0.1:8000/api/v1/health  
- UI: http://127.0.0.1:3000  
- پس از login tenant: `/knowledge` و `/bots`  
- راهنمای پلتفرم: [multi-tenant.fa.md](./multi-tenant.fa.md)

## استک کامل داخل Docker

```powershell
.\scripts\stack-up.ps1
```

استقرار چابکان / آینه: [deployment.fa.md](./deployment.fa.md)

## تست

```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```
