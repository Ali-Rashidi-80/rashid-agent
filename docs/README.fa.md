# مستندات همیار کد رشید

[English](README.md) | **فارسی**

ایندکس اسناد. فایل‌های انگلیسی پیش‌فرض‌اند؛ نسخهٔ فارسی با پسوند `.fa.md` یا `*-fa.md`.

## شروع سریع

| سند | موضوع |
|-----|--------|
| [quickstart-fa.md](./quickstart-fa.md) | راه‌اندازی hybrid · [EN](./quickstart.md) |
| [deployment.fa.md](./deployment.fa.md) | Docker کامل، چابکان، local-mirror · [EN](./deployment.md) |
| [mirrors-iran-fa.md](./mirrors-iran-fa.md) | میرور چابکان / آروان · [EN](./mirrors-iran.md) |
| [infrastructure.fa.md](./infrastructure.fa.md) | Postgres، Redis، worker، health · [EN](./infrastructure.md) |
| [architecture.fa.md](./architecture.fa.md) | لایه‌ها و اجزا · [EN](./architecture.md) |

## پلتفرم چندمستأجری و کانال‌ها

| سند | موضوع |
|-----|--------|
| [multi-tenant.fa.md](./multi-tenant.fa.md) | tenant، RLS، seed، داشبورد · [EN](./multi-tenant.md) |
| [knowledge-ingest.fa.md](./knowledge-ingest.fa.md) | آپلود، OCR، ARQ، embedding · [EN](./knowledge-ingest.md) |
| [erp-rag-bridge.fa.md](./erp-rag-bridge.fa.md) | پل ERP → KB · [EN](./erp-rag-bridge.md) |
| [telegram.fa.md](./telegram.fa.md) | webhook، OTP، long-poll · [EN](./telegram.md) |
| [bale.fa.md](./bale.fa.md) | اتصال بله · [EN](./bale.md) |
| [agent-protocol.fa.md](./agent-protocol.fa.md) | رویدادهای SSE · [EN](./agent-protocol.md) |

## یک خط — توسعه hybrid

```powershell
.\scripts\setup-mirrors.ps1; .\scripts\infra-up.ps1; pip install -e ".[dev]"; .\scripts\migrate.ps1; .\scripts\dev.ps1
```

Frontend (ترمینال جدا):

```powershell
cd frontend; copy .env.example .env.local; npm install; npm run dev
```

## یک خط — استک کامل Docker

```powershell
copy .env.example .env
.\scripts\setup-mirrors.ps1
.\scripts\stack-up.ps1
```

## یک خط — کانتینر خام چابکان + آینهٔ لوکال

```powershell
.\scripts\chabokan-stack-up.ps1
.\scripts\local-mirror-up.ps1
```

تست زنده:

```powershell
python scripts/live_docker_stack_test.py
```

قالب env بدون secret: `.env.example` · `backend/.env.example` · `frontend/.env.example` · `.env.local-mirror.example`

نمای کلی مخزن: [../README.fa.md](../README.fa.md) · [English](../README.md)
