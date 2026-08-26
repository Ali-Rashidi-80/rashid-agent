# چندمستأجری (Multi-tenant) — رشید

[English](multi-tenant.md) | **فارسی**

## مدل

هر **tenant** (کارفرما/سازمان) دادهٔ خود را جدا دارد:

```
tenant
  ├── tenant_admins          # ورود داشبورد /knowledge و /bots
  ├── knowledge_bases        # اسناد + chunk + embedding (pgvector)
  ├── org_bots               # بات عمومی /b/[slug] + OTP
  └── messenger_integrations # تلگرام/بله → org_bot → KB
```

جداسازی KB در Postgres با **RLS** و نقش اپلیکیشن `rashid_app` (بدون `BYPASSRLS`) اعمال می‌شود. جزئیات مهاجرت‌ها در `backend/alembic/versions/`.

## Seed پیش‌فرض: عدل امید

با پر بودن در `.env`:

- `TENANT_SEED_ADMIN_USER`
- `TENANT_SEED_ADMIN_PASSWORD`
- `TENANT_SEED_CODE_PROJECT_PATH` (مسیر پروژهٔ کد برای agent)

در استارت API، tenant با slug `adl-omid` و ادمین seed می‌شود (اگر نبود).

ورود API:

```http
POST /api/v1/tenants/login
{"username":"...","password":"..."}
```

توکن را به‌صورت `Authorization: Bearer <access_token>` برای KB / org-bots / integrations بفرستید.

## جریان عملیاتی ادمین

1. ورود به UI → `/knowledge` — ساخت پایگاه دانش، آپلود اسناد (OCR/ARQ برای فایل بزرگ)
2. `/bots` — ساخت `org_bot` روی همان KB، صدور OTP برای مخاطب
3. اختیاری: صفحهٔ عمومی `/b/<slug>` با OTP
4. اختیاری: `POST /api/v1/integrations` برای تلگرام/بله — [telegram.fa.md](./telegram.fa.md) / [bale.fa.md](./bale.fa.md)
5. اختیاری: همگام ERP RAG — [erp-rag-bridge.fa.md](./erp-rag-bridge.fa.md)

## امنیت

- توکن بات را فقط از integrations API ذخیره کنید (رمز با `SECRETS_ENCRYPTION_KEY`)
- OTP را خارج از کانال عمومی بدهید
- `RASHID_TOKEN` قفل سراسری API است و جایگزین auth tenant نیست
- هرگز `.env` را commit نکنید

## تست‌های مرتبط

- `backend/tests/test_tenants_api.py`
- `backend/tests/test_kb_rls.py`
- `backend/tests/test_org_bots_api.py`
- `backend/tests/test_telegram_webhook.py`
