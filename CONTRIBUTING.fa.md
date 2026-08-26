# مشارکت در همیار کد رشید

[English](CONTRIBUTING.md) | **فارسی**

از کمک شما برای بهبود رشید سپاسگزاریم. این راهنما مسیر پیش‌فرض مشارکت در کد و مستندات است.

## اصول همکاری

- PRها را متمرکز نگه دارید.
- با الگوهای موجود در `backend/` و `frontend/` هم‌خوان باشید.
- secretها را commit نکنید (`.env`، توکن، OTP، کلید خصوصی).
- ابزار تهاجمی امنیتی یا دسترسی غیرمجاز اضافه نکنید.

## راه‌اندازی توسعه

[docs/quickstart-fa.md](docs/quickstart-fa.md) را دنبال کنید. حداقل حلقه:

```powershell
.\scripts\setup-mirrors.ps1
copy .env.example .env
# METIS_API_KEY ، SECRETS_ENCRYPTION_KEY ، TENANT_SEED_* ، POSTGRES_PASSWORD
pip install -e ".[dev]"
.\scripts\infra-up.ps1
.\scripts\migrate.ps1
.\scripts\dev.ps1
```

فرانت (ترمینال دوم):

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

## شاخه و PR

1. از شاخهٔ فعال توسعه انشعاب بگیرید.
2. برای تغییر رفتار، تست بنویسید یا به‌روز کنید.
3. چک‌های محلی را اجرا کنید.
4. PR با توضیح **چرا**، ریسک، و نحوهٔ تست باز کنید.

## چک قبل از push

```powershell
python -m ruff check backend
python -m black --check backend
python -m isort --check-only backend
python -m flake8 backend --max-line-length=100 --extend-ignore=E501,W503,E203
$env:PYTHONPATH="backend"
python -m pytest backend/tests -q
```

## مستندات

- **زبان پیش‌فرض انگلیسی** است (`README.md`، `docs/*.md`).
- نسخهٔ فارسی: `README.fa.md`، `docs/*.fa.md` یا `docs/*-fa.md`.
- با تغییر رفتار، در صورت امکان هر دو زبان را در همان PR به‌روز کنید.
- دیاگرام‌های سالم را بدون جایگزین حذف نکنید.

## گزارش باگ

در GitHub Issues بنویسید: رفتار مورد انتظار/واقعی، گام‌های بازتولید، لاگ (بدون secret)، نسخهٔ OS/Python/Node/Docker.

## مجوز

با مشارکت، می‌پذیرید که مشارکت‌تان تحت همان [MIT License](LICENSE) منتشر شود.
