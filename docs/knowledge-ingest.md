# Knowledge base — ingest, OCR, ARQ

**English** | [فارسی](knowledge-ingest.fa.md)

Tenant isolation and RLS: [multi-tenant.md](./multi-tenant.md) · Deploy: [deployment.md](./deployment.md)

## Flow

1. Tenant admin authenticates with Bearer (`POST /api/v1/tenants/login`)
2. `POST /api/v1/knowledge-bases` — create KB (+ system prompt)
3. Upload document to KB → extract text → chunk → embed (Metis) → `status=ready|partial|failed`
4. Retrieve in Ask / org_bot / Telegram only from that KB

UI: `/knowledge` after tenant login.

## Image OCR

For `png/jpg/jpeg/webp/gif` engine order:

1. **RapidOCR** (local, pip dependency)
2. **Tesseract** if installed (`fas+eng` then `eng`)
3. **Metis vision** (`KB_OCR_VISION_MODEL`, default `gpt-4o-mini`) if API key present

If text is extracted → `status=ready`; if empty → `status=partial` and `error_message=image_ocr_empty`.

## ARQ for large files

- Threshold: `KB_ARQ_INGEST_MIN_BYTES` (default 1MB)
- Job: `job_kb_ingest`
- Local: `scripts/smoke-worker.ps1 start` or compose `worker`
- If worker is unavailable, the same upload request ingests inline

## Upload and storage limits

- `KB_MAX_UPLOAD_BYTES` (default 25MB) → `413` / `file_too_large`
- Files under `KB_STORAGE_DIR` or default `backend/data/kb`
- Embedding: `KB_EMBEDDING_MODEL`; offline/test `KB_EMBED_HASH_FALLBACK=true` (dev only)

## Related `.env` settings

`KB_CHUNK_SIZE` · `KB_CHUNK_OVERLAP` · `KB_TOP_K` · `KB_OCR_VISION_MODEL` · `METIS_API_KEY`
