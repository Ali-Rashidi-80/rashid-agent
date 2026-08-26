# پایگاه دانش — ingest، OCR، ARQ

[English](knowledge-ingest.md) | **فارسی**

جداسازی tenant و RLS: [multi-tenant.fa.md](./multi-tenant.fa.md) · استقرار: [deployment.fa.md](./deployment.fa.md)

## جریان

1. ادمین tenant با Bearer وارد می‌شود (`POST /api/v1/tenants/login`)
2. `POST /api/v1/knowledge-bases` — ساخت KB (+ system prompt)
3. آپلود سند به KB → استخراج متن → chunk → embedding (Metis) → `status=ready|partial|failed`
4. بازیابی در Ask / org_bot / تلگرام فقط از همان KB

UI: `/knowledge` پس از login tenant.

## OCR تصویر

برای `png/jpg/jpeg/webp/gif` ترتیب موتورها:

1. **RapidOCR** (لوکال، وابستگی pip)
2. **Tesseract** اگر نصب باشد (`fas+eng` سپس `eng`)
3. **Metis vision** (`KB_OCR_VISION_MODEL`, پیش‌فرض `gpt-4o-mini`) اگر API key باشد

اگر متن استخراج شود → `status=ready`؛ اگر خالی بماند → `status=partial` و `error_message=image_ocr_empty`.

## ARQ برای فایل بزرگ

- آستانه: `KB_ARQ_INGEST_MIN_BYTES` (پیش‌فرض ۱MB)
- Job: `job_kb_ingest`
- لوکال: `scripts/smoke-worker.ps1 start` یا worker کانتینر در Compose
- اگر worker در دسترس نباشد، همان درخواست upload به‌صورت inline ingest می‌شود

## سقف آپلود و ذخیره

- `KB_MAX_UPLOAD_BYTES` (پیش‌فرض ۲۵MB) → `413` / `file_too_large`
- فایل‌ها زیر `KB_STORAGE_DIR` یا پیش‌فرض `backend/data/kb`
- Embedding: `KB_EMBEDDING_MODEL`؛ در تست/آفلاین `KB_EMBED_HASH_FALLBACK=true` (فقط dev)

## تنظیمات مرتبط در `.env`

`KB_CHUNK_SIZE` · `KB_CHUNK_OVERLAP` · `KB_TOP_K` · `KB_OCR_VISION_MODEL` · `METIS_API_KEY`
