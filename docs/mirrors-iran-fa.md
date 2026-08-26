# میرورهای ایران — رشید ایجنت

[English](mirrors-iran.md) | **فارسی**

## گام ۰ (اجباری روی ماشین توسعه)

```powershell
.\scripts\setup-mirrors.ps1
.\scripts\verify-mirrors.ps1
```

## پیش‌فرض: چابکان

| لایه | URL / تصویر |
|------|-------------|
| PyPI | `https://mirror2.chabokan.net/pypi/simple/` |
| npm | `https://mirror2.chabokan.net/npm/` |
| Docker Hub proxy | `mirror2.chabokan.net` |
| Python image | `mirror2.chabokan.net/library/python:3.11-slim-bookworm` |
| Node image | `mirror2.chabokan.net/library/node:20-alpine` |
| Postgres+pgvector | `mirror2.chabokan.net/pgvector/pgvector:pg16` |
| Redis | `mirror2.chabokan.net/library/redis:7-alpine` |
| Debian apt (در Dockerfile) | `https://mirror2.chabokan.net/debian` |

پیکربندی میزبان: `config/mirrors/chabokan.env`  
قالب‌ها: `config/mirrors/pip.ini.template` · `.npmrc.template` · `daemon.json.template`  
داخل ایمیج: `docker/pip-chabokan.conf` · `docker/apt-chabokan-bookworm.sh` · `backend/pip.conf`

## Docker Desktop (Windows)

Settings → Docker Engine → محتوای `config/mirrors/daemon.json.template` را ادغام کنید (حداقل `registry-mirrors`).

## بیلد کانتینر

Dockerfileهای `backend/` و `frontend/` و همهٔ composeها به‌صورت پیش‌فرض از میرور چابکان می‌کشند.  
Override در `.env`:

```env
PYTHON_IMAGE=...
NODE_IMAGE=...
POSTGRES_IMAGE=...
REDIS_IMAGE=...
```

اگر تگ روی میرور نبود، به تصویر Docker Hub برگردید؛ با `registry-mirrors` باز هم از چابکان پروکسی می‌شود.

Fallback داخل بیلد: یک‌بار retry به `pypi.org` / `registry.npmjs.org` اگر میرور پکیج را نداشت.

## Fallback آروان

```powershell
.\scripts\setup-mirrors.ps1 -Profile arvan
```

## بدون میرور

```powershell
.\scripts\setup-mirrors.ps1 -Profile direct
```

نیاز به VPN یا دسترسی مستقیم به Docker Hub / PyPI / npm.
