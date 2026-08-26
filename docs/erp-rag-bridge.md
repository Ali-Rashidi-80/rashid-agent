# ERP RAG bridge → Rashid knowledge base (Phase E)

**English** | [فارسی](erp-rag-bridge.fa.md)

Optional sync of knowledge from LiquidGlass Legal ERP into the same tenant KB in Rashid (e.g. `adl-omid`). It does **not** replace Rashid’s multi-tenant model.

## Flow

```text
Staff JWT (ERP) → GET /api/v1/ai/rag/retrieve
                 → erp__* documents in Rashid KB
                 → local chunk/embed in Rashid
```

- Default ERP collections: `firm`, `cases`, `approved_drafts`
- Stable filename: `erp__{collection}__{sourceType}__{sourceId}.txt`
- Re-running the same query **updates** the same document (no endless duplicates)

## Prerequisites

1. ERP reachable (local or staging)
2. In Rashid `.env`:

```env
ERP_RAG_BASE_URL=http://127.0.0.1:8001
# Optional — if you do not pass access_token in the request:
ERP_RAG_USERNAME=staff_user
ERP_RAG_PASSWORD=...
```

3. Rashid tenant admin logged in (e.g. Adl Omid seed)

## API

```http
POST /api/v1/knowledge-bases/{kb_id}/erp-sync
Authorization: Bearer <tenant-admin-token>
Content-Type: application/json

{
  "queries": ["leave policy", "transaction capacity"],
  "collections": ["firm", "approved_drafts"],
  "limit": 8,
  "access_token": "<optional ERP staff JWT>"
}
```

Sample response:

```json
{
  "chunks_fetched": 3,
  "documents_created": 2,
  "documents_updated": 1,
  "documents": [{ "id": "...", "filename": "erp__firm__policy__leave-1.txt", "status": "ready" }]
}
```

Common errors: `erp_rag_not_configured` (503), `erp_credentials_required` (400), `erp_unauthorized` (401).

## UI

On `/knowledge`, after selecting a KB, use “Sync from ERP” with a search phrase. Server needs `ERP_RAG_*` credentials (or a request `access_token`).

## Related

- Image OCR during ingest: RapidOCR (local) + optional Tesseract/Metis vision
- Large files (≥ `KB_ARQ_INGEST_MIN_BYTES`) ingest via ARQ worker (`scripts/smoke-worker.ps1 start`)

## Security

- Do not log ERP JWT/passwords
- Only the same tenant admin can sync into their KB
- ERP content is indexed only inside that tenant KB (RLS)
- Do not put ERP staff tokens in git
