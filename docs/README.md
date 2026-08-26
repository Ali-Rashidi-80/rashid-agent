# Rashid Agent — Documentation

**English** | [فارسی](README.fa.md)

Index of project docs. English files are the default; Persian siblings use `.fa.md` or `*-fa.md`.

## Getting started

| Doc | Topic |
|-----|--------|
| [quickstart.md](./quickstart.md) | Hybrid setup (host + Docker infra) · [FA](./quickstart-fa.md) |
| [deployment.md](./deployment.md) | Full Docker, Chabokan, local-mirror · [FA](./deployment.fa.md) |
| [mirrors-iran.md](./mirrors-iran.md) | Chabokan / Arvan mirrors · [FA](./mirrors-iran-fa.md) |
| [infrastructure.md](./infrastructure.md) | Postgres, Redis, worker, health · [FA](./infrastructure.fa.md) |
| [architecture.md](./architecture.md) | Layers and components · [FA](./architecture.fa.md) |

## Multi-tenant platform & channels

| Doc | Topic |
|-----|--------|
| [multi-tenant.md](./multi-tenant.md) | Tenant, RLS, seed, dashboard · [FA](./multi-tenant.fa.md) |
| [knowledge-ingest.md](./knowledge-ingest.md) | Upload, OCR, ARQ, embedding · [FA](./knowledge-ingest.fa.md) |
| [erp-rag-bridge.md](./erp-rag-bridge.md) | ERP Liquidglass → KB · [FA](./erp-rag-bridge.fa.md) |
| [telegram.md](./telegram.md) | Webhook, OTP, long-poll bridge · [FA](./telegram.fa.md) |
| [bale.md](./bale.md) | Bale connection · [FA](./bale.fa.md) |
| [agent-protocol.md](./agent-protocol.md) | SSE events · [FA](./agent-protocol.fa.md) |

## One-liners

### Hybrid development

```powershell
.\scripts\setup-mirrors.ps1; .\scripts\infra-up.ps1; pip install -e ".[dev]"; .\scripts\migrate.ps1; .\scripts\dev.ps1
```

Frontend (separate terminal):

```powershell
cd frontend; copy .env.example .env.local; npm install; npm run dev
```

### Full Docker stack

```powershell
copy .env.example .env
.\scripts\setup-mirrors.ps1
.\scripts\stack-up.ps1
```

### Chabokan raw + local mirror

```powershell
.\scripts\chabokan-stack-up.ps1
.\scripts\local-mirror-up.ps1
```

Live test (build + up + health + login):

```powershell
python scripts/live_docker_stack_test.py
```

## Env templates (no secrets)

`.env.example` · `backend/.env.example` · `frontend/.env.example` · `.env.local-mirror.example` · `.env.chabokan.split.example`

Root overview: [../README.md](../README.md) · [فارسی](../README.fa.md)

Brand: [../brand/PROMPT.md](../brand/PROMPT.md) · logo [`assets/rashid-agent-logo-3d.png`](./assets/rashid-agent-logo-3d.png)
