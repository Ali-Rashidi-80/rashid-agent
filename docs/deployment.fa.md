# استقرار Docker / چابکان — همیار کد رشید

[English](deployment.md) | **فارسی**

## سه حالت استقرار

| حالت | فایل | کانتینرها | کاربرد |
|------|------|-----------|--------|
| Hybrid dev | `docker-compose.yml` | فقط `postgres` + `redis` (پیش‌فرض) | API/فرانت روی host |
| Full local | `docker-compose.yml --profile full` | + `migrate` `api` `worker` `web` | استک کامل لوکال |
| Chabokan raw | `docker-compose.chabokan.yml` | `rashid-chabokan-*` | VPS / کانتینر خام ریموت |
| Local mirror (DR) | `docker-compose.local-mirror.yml` | `rashid-mirror-*` | کلون DR مثل Liquidglass |
| Backend split | `backend/docker-compose.yml` | API (+ اختیاری db/redis) | پنل جدا از وب |

## میرور چابکان (الزامی برای بیلد در ایران)

همهٔ `FROM` / `image` پیش‌فرض از `mirror2.chabokan.net`:

| لایه | مقدار |
|------|--------|
| Python | `mirror2.chabokan.net/library/python:3.11-slim-bookworm` |
| Node | `mirror2.chabokan.net/library/node:20-alpine` |
| Postgres+pgvector | `mirror2.chabokan.net/pgvector/pgvector:pg16` |
| Redis | `mirror2.chabokan.net/library/redis:7-alpine` |
| PyPI | `https://mirror2.chabokan.net/pypi/simple/` |
| npm | `https://mirror2.chabokan.net/npm/` |
| Debian apt | `https://mirror2.chabokan.net/debian` |

میزبان: `.\scripts\setup-mirrors.ps1` و `docs/mirrors-iran-fa.md`.  
اگر تگ روی میرور نبود، در `.env` مثلاً `POSTGRES_IMAGE=pgvector/pgvector:pg16` بگذارید (با `daemon.json` میرور).

## راه‌اندازی سریع — استک کامل لوکال

```powershell
copy .env.example .env
# در `.env` مقادیر حساس را پر کنید (فایل‌های *.example عمداً خالی‌اند)
.\scripts\setup-mirrors.ps1
.\scripts\stack-up.ps1
```

- Web: http://127.0.0.1:3000  
- API: http://127.0.0.1:8000/api/v1/health  

## راه‌اندازی — کانتینر خام چابکان / ریموت

```powershell
copy .env.example .env
# POSTGRES_PASSWORD و SECRETS_ENCRYPTION_KEY الزامی
.\scripts\chabokan-stack-up.ps1
```

یا:

```bash
DOCKER_BUILDKIT=1 docker compose -f docker-compose.chabokan.yml --env-file .env build
docker compose -f docker-compose.chabokan.yml --env-file .env up -d
```

کانتینرها:

- `rashid-chabokan-postgres`
- `rashid-chabokan-redis`
- `rashid-chabokan-api`
- `rashid-chabokan-worker`
- `rashid-chabokan-web`
- `rashid-chabokan-migrate` (یک‌بار)

برای TLS و دامنه عمومی، جلوی `web`/`api` یک reverse proxy (Nginx/Caddy) بگذارید.  
Webhook تلگرام: `https://<HOST>/api/v1/integrations/telegram/webhook/<integration_id>` — نکته‌ها در [telegram.fa.md](./telegram.fa.md).

## Local mirror (کانتینرهای آینه)

الگوی نام‌گذاری مثل Liquidglass (`lg-mirror-*`) → اینجا `rashid-mirror-*`:

```powershell
copy .env.local-mirror.example .env.local-mirror
# LOCAL_DB_PASSWORD و REDIS_PASSWORD را عوض کنید
.\scripts\local-mirror-up.ps1
```

| کانتینر | نقش |
|---------|-----|
| `rashid-mirror-db` | Postgres + pgvector |
| `rashid-mirror-redis` | Redis با رمز |
| `rashid-mirror-api` | FastAPI |
| `rashid-mirror-worker` | ARQ |
| `rashid-mirror-web` | Next.js |

پورت‌های پیش‌فرض لوکال: API `8001`، Web `3001`، DB `5433`، Redis `6381` (فقط `127.0.0.1`).

## استقرار جدا (وب / API) روی پنل چابکان

چک‌لیست متغیرها: `.env.chabokan.split.example`  
DB/Redis مدیریت‌شدهٔ چابکان را در `DATABASE_URL` / `REDIS_URL` بگذارید؛ نیازی به سرویس `db` داخل compose نیست.

```bash
# فقط API (+ worker) با تصویر بکند
cd backend
docker compose --env-file ../.env up -d api worker
# برای DB/Redis داخل همین فایل: --profile with-db
```

فرانت: بیلد `frontend/Dockerfile` با `BACKEND_URL=https://api.YOUR_DOMAIN`.

## متغیرهای حیاتی production

| متغیر | چرا |
|--------|-----|
| `SECRETS_ENCRYPTION_KEY` | رمز توکن بات در DB |
| `POSTGRES_PASSWORD` | DB |
| `METIS_API_KEY` | LLM + embeddings |
| `TENANT_SEED_ADMIN_*` | ادمین tenant اول (adl-omid) |
| `RASHID_TOKEN` | اختیاری؛ قفل API سراسری |
| `TELEGRAM_*` | فقط seed/dev؛ ترجیح integrations API |
| `SMS_CONSOLE_API_TOKEN` / `SMS_PROVIDER_MODE` | OTP پیامکی ملّی‌پیامک (پترن `477732`)؛ لوکال معمولاً `stub` |
| Docker build | `DOCKER_BUILDKIT=1` — لایهٔ pip + cache mount تا وابستگی‌ها هر بار دانلود نشوند |

فرانت host: `frontend/.env.example` → `.env.local`.

## Health

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:3000/fa
```

پاسخ health باید `postgres` / `redis` / `worker` را `ok` نشان دهد (وقتی worker بالا باشد).

## Migrate

کانتینر `migrate` (یا entrypoint `backend/start.sh`) قبل از `api`، `alembic upgrade head` را اجرا می‌کند.  
برای رد کردن migrate روی یک سرویس: `RASHID_SKIP_MIGRATE=1`.

## قالب‌های env (بدون secret)

| فایل | نقش |
|------|-----|
| `.env.example` | ریشه / بکند (template) |
| `backend/.env.example` | یادآوری بارگذاری از root `.env` |
| `frontend/.env.example` | Next.js host |
| `.env.local-mirror.example` | آینه DR |
| `.env.chabokan.split.example` | چک‌لیست پنل چابکان |

همهٔ فیلدهای حساس در exampleها **خالی** می‌مانند.

## تست زندهٔ همهٔ کانتینرها

اسکریپت env موقت (gitignored) می‌سازد، هر دو استک را build/up می‌کند و health + login را چک می‌کند:

```powershell
python scripts/live_docker_stack_test.py
```

پورت‌های پیش‌فرض تست (برای جلوگیری از تداخل hybrid): API `28000` / Web `23000` (chabokan) و API `8001` / Web `3001` (mirror).  
خلاصهٔ غیرحساس: `backend/data/live_docker_stack_note.txt`
