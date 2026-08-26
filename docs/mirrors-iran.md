# Iran mirrors — Rashid Agent

**English** | [فارسی](mirrors-iran-fa.md)

## Step 0 (required on the development machine)

```powershell
.\scripts\setup-mirrors.ps1
.\scripts\verify-mirrors.ps1
```

## Default: Chabokan

| Layer | URL / image |
|-------|-------------|
| PyPI | `https://mirror2.chabokan.net/pypi/simple/` |
| npm | `https://mirror2.chabokan.net/npm/` |
| Docker Hub proxy | `mirror2.chabokan.net` |
| Python image | `mirror2.chabokan.net/library/python:3.11-slim-bookworm` |
| Node image | `mirror2.chabokan.net/library/node:20-alpine` |
| Postgres+pgvector | `mirror2.chabokan.net/pgvector/pgvector:pg16` |
| Redis | `mirror2.chabokan.net/library/redis:7-alpine` |
| Debian apt (in Dockerfile) | `https://mirror2.chabokan.net/debian` |

Host config: `config/mirrors/chabokan.env`  
Templates: `config/mirrors/pip.ini.template` · `.npmrc.template` · `daemon.json.template`  
Inside images: `docker/pip-chabokan.conf` · `docker/apt-chabokan-bookworm.sh` · `backend/pip.conf`

## Docker Desktop (Windows)

Settings → Docker Engine → merge `config/mirrors/daemon.json.template` (at least `registry-mirrors`).

## Container builds

`backend/` and `frontend/` Dockerfiles and all compose files pull from the Chabokan mirror by default.  
Override in `.env`:

```env
PYTHON_IMAGE=...
NODE_IMAGE=...
POSTGRES_IMAGE=...
REDIS_IMAGE=...
```

If a tag is missing on the mirror, fall back to the Docker Hub image name; with `registry-mirrors` it still proxies via Chabokan.

In-build fallback: one retry to `pypi.org` / `registry.npmjs.org` if the mirror lacks a package.

## Arvan fallback

```powershell
.\scripts\setup-mirrors.ps1 -Profile arvan
```

## No mirror

```powershell
.\scripts\setup-mirrors.ps1 -Profile direct
```

Requires VPN or direct access to Docker Hub / PyPI / npm.
