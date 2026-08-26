# پل ERP RAG → پایگاه دانش رشید (فاز E)

[English](erp-rag-bridge.md) | **فارسی**

همگام‌سازی **اختیاری** دانش از LiquidGlass Legal ERP به KB همان tenant در رشید (مثلاً `adl-omid`). جایگزین مدل چندکارفرمایی رشید نیست.

## جریان

```
Staff JWT (ERP) → GET /api/v1/ai/rag/retrieve
                 → اسناد erp__* در KB رشید
                 → chunk/embed محلی رشید
```

- کالکشن‌های پیش‌فرض ERP: `firm`, `cases`, `approved_drafts`
- نام فایل پایدار: `erp__{collection}__{sourceType}__{sourceId}.txt`
- اجرای دوباره همان query همان سند را **به‌روز** می‌کند (نه تکراری بی‌پایان)

## پیش‌نیاز

1. ERP در دسترس باشد (لوکال یا staging)
2. در `.env` رشید:

```env
ERP_RAG_BASE_URL=http://127.0.0.1:8001
# اختیاری — اگر access_token در درخواست ندهید:
ERP_RAG_USERNAME=staff_user
ERP_RAG_PASSWORD=...
```

3. ادمین tenant رشید (مثلاً seed عدل‌امید) وارد شده باشد

## API

```http
POST /api/v1/knowledge-bases/{kb_id}/erp-sync
Authorization: Bearer <tenant-admin-token>
Content-Type: application/json

{
  "queries": ["سیاست مرخصی", "اهلیت معامله"],
  "collections": ["firm", "approved_drafts"],
  "limit": 8,
  "access_token": "<optional ERP staff JWT>"
}
```

پاسخ نمونه:

```json
{
  "chunks_fetched": 3,
  "documents_created": 2,
  "documents_updated": 1,
  "documents": [{ "id": "...", "filename": "erp__firm__policy__leave-1.txt", "status": "ready" }]
}
```

خطاهای رایج: `erp_rag_not_configured` (503)، `erp_credentials_required` (400)، `erp_unauthorized` (401).

## UI

در صفحهٔ `/knowledge` پس از انتخاب KB، فیلد «همگام‌سازی از ERP» را با یک عبارت جستجو پر کنید. سرور از env credentials یا باید `ERP_RAG_*` ست شده باشد.

## مرتبط

- OCR تصویر در ingest: RapidOCR (لوکال) + اختیاری Tesseract/Metis vision
- فایل‌های بزرگ (≥ `KB_ARQ_INGEST_MIN_BYTES`) با ARQ worker اینجست می‌شوند (`scripts/dev-worker.ps1` یا `scripts/smoke-worker.ps1 start`)

## امنیت

- JWT/رمز ERP را در لاگ ننویسید
- فقط ادمین همان tenant می‌تواند به KB خودش sync کند
- محتوای ERP فقط داخل KB همان tenant ایندکس می‌شود (RLS)
- توکن staff ERP را در git نگذارید
