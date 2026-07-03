# Architecture — Rashid Agent v2

## Layers

```
Browser → Next.js (BFF :3000) → FastAPI (:8000) → Postgres + Redis
                                      ↓
                                 ARQ Worker → Metis API
```

## Backend (`backend/app/`)

- `routers/` — HTTP thin layer
- `services/` — orchestration (metis, context, patch)
- `domain/` — pure logic (patch_engine)
- `db/repositories/` — persistence
- `prompts/` — Prompt Registry

## Frontend (`frontend/src/`)

- `features/` — chat, diff, settings
- `app/api/v1/` — BFF proxy to backend

See plan section هـ.۵ for dependency rules.
