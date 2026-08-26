# Contributing to Rashid Agent

**English** | [فارسی](CONTRIBUTING.fa.md)

Thanks for helping improve Rashid Agent. This guide covers the default workflow for code and docs.

## Code of collaboration

- Keep PRs focused: one concern per PR when practical.
- Prefer clarity over cleverness; match existing patterns in `backend/` and `frontend/`.
- Do not commit secrets (`.env`, tokens, OTP codes, private keys).
- Do not add offensive security PoCs, malware, or unauthorized-access tooling.

## Development setup

Follow [docs/quickstart.md](docs/quickstart.md). Minimum loop:

```powershell
.\scripts\setup-mirrors.ps1
copy .env.example .env
# fill METIS_API_KEY, SECRETS_ENCRYPTION_KEY, TENANT_SEED_*, POSTGRES_PASSWORD
pip install -e ".[dev]"
.\scripts\infra-up.ps1
.\scripts\migrate.ps1
.\scripts\dev.ps1
```

Frontend (second terminal):

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

## Branch & PR

1. Branch from the active development branch (see repo default / `feature/rashid-agent-v2`).
2. Make your change with tests when behavior changes.
3. Run local checks (below).
4. Open a PR describing **why**, risk, and how you tested.

## Checks before push

```powershell
python -m ruff check backend
python -m black --check backend
python -m isort --check-only backend
python -m flake8 backend --max-line-length=100 --extend-ignore=E501,W503,E203
$env:PYTHONPATH="backend"
python -m pytest backend/tests -q
```

Frontend (when touching UI):

```powershell
cd frontend
npm run lint
# optional: npm test / playwright as configured in the package
```

CI mirrors these steps in [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Documentation

- **English is the default** for `README.md` and `docs/*.md`.
- Persian siblings live as `README.fa.md`, `docs/*.fa.md`, or `docs/*-fa.md`.
- When you change behavior, update both EN and FA docs in the same PR when possible.
- Keep diagrams (ASCII / Mermaid) accurate; do not delete working diagrams without replacement.

## Project conventions

| Area | Convention |
|------|------------|
| Python | 3.11+, black/isort/ruff, line length 100 |
| Backend layout | thin routers → services → domain / repositories |
| Tenant data | respect RLS; never bypass isolation in app code |
| Env templates | secrets empty in `*.example` files |
| Legacy | do not extend `legacy/` |

## Reporting bugs

Use GitHub Issues with:

- Expected vs actual behavior
- Repro steps (hybrid vs compose mode)
- Relevant logs (redact secrets)
- Versions: OS, Python, Node, Docker

## License

By contributing, you agree that your contributions are licensed under the same [MIT License](LICENSE) as the project.
