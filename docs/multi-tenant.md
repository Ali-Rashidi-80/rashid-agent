# Multi-tenant — Rashid Agent

**English** | [فارسی](multi-tenant.fa.md)

## Model

Each **tenant** (org / employer) keeps its own data:

```text
tenant
  ├── tenant_admins          # dashboard login for /knowledge and /bots
  ├── knowledge_bases        # documents + chunks + embeddings (pgvector)
  ├── org_bots               # public bot /b/[slug] + OTP
  └── messenger_integrations # Telegram/Bale → org_bot → KB
```

KB isolation is enforced in Postgres with **RLS** and application role `rashid_app` (no `BYPASSRLS`). Migration details live under `backend/alembic/versions/`.

## Default seed: Adl Omid

When set in `.env`:

- `TENANT_SEED_ADMIN_USER`
- `TENANT_SEED_ADMIN_PASSWORD`
- `TENANT_SEED_CODE_PROJECT_PATH` (code project path for the agent)

On API start, tenant slug `adl-omid` and admin are seeded if missing.

Login API:

```http
POST /api/v1/tenants/login
{"username":"...","password":"..."}
```

Send the token as `Authorization: Bearer <access_token>` for KB / org-bots / integrations.

## Admin operating flow

1. UI login → `/knowledge` — create KB, upload docs (OCR/ARQ for large files)
2. `/bots` — create `org_bot` on that KB, issue OTP for contacts
3. Optional: public page `/b/<slug>` with OTP
4. Optional: `POST /api/v1/integrations` for Telegram/Bale — [telegram.md](./telegram.md) / [bale.md](./bale.md)
5. Optional: ERP RAG sync — [erp-rag-bridge.md](./erp-rag-bridge.md)

## Security

- Store bot tokens only via the integrations API (encrypted with `SECRETS_ENCRYPTION_KEY`)
- Deliver OTP outside public channels
- `RASHID_TOKEN` is a global API lock — not a tenant-auth substitute
- Never commit `.env`

## Related tests

- `backend/tests/test_tenants_api.py`
- `backend/tests/test_kb_rls.py`
- `backend/tests/test_org_bots_api.py`
- `backend/tests/test_telegram_webhook.py`
