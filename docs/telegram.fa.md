# راهنمای اتصال تلگرام به رشید (فاز D)

[English](telegram.md) | **فارسی**

## معماری

هر ربات تلگرام = یک ردیف `messenger_integrations` → یک `org_bot` → یک `knowledge_base` → یک `tenant`.

- Webhook: `POST /api/v1/integrations/telegram/webhook/{integration_id}`
- هدر اجباری: `X-Telegram-Bot-Api-Secret-Token` (مقایسه timing-safe با `webhook_secret`)
- توکن بات در DB رمزگذاری‌شده (`SECRETS_ENCRYPTION_KEY`)
- دستورات: `/start` `/help` `/login <کد>` `/logout` `/status`
- پس از `/login` موفق، `chat_id` در `messenger_links` ذخیره می‌شود
- سؤال‌ها فقط Ask + RAG روی KB همان `org_bot`

## پیش‌نیاز

1. فاز B (KB) و C (org_bot + OTP) آماده باشد
2. `SECRETS_ENCRYPTION_KEY` در `.env` (رشتهٔ تصادفی بلند)
3. HTTPS عمومی برای webhook (یا تونل توسعه). اگر تونل از شبکهٔ شما timeout شد، برای توسعهٔ لوکال:

```bash
python scripts/telegram_longpoll_bridge.py
```

این اسکریپت `deleteWebhook` می‌زند و `getUpdates` را به webhook لوکال فوروارد می‌کند — همان هدر `X-Telegram-Bot-Api-Secret-Token`.

برای استک آینه (`rashid-mirror-*` روی `:8001`):

```bash
python scripts/bootstrap_mirror_telegram.py
python scripts/telegram_longpoll_bridge.py
```

`api_base` از فایل خلاصهٔ bootstrap خوانده می‌شود (`http://127.0.0.1:8001`).

## پروفایل و متون حرفه‌ای بات

اعمال نام، توضیح کوتاه، توضیح کامل («What can this bot do?»)، و فهرست دستورات از API:

```bash
python scripts/apply_telegram_bot_profile.py
```

خروجی JSON در `backend/data/telegram_botfather_paste.json` شامل متن‌های Mini App / Direct Link است (این بخش‌ها فقط از BotFather قابل ویرایش‌اند).

منبع متن‌ها: `backend/app/services/telegram_bot_profile.py`

## ساخت integration از API

با توکن ادمین tenant:

```http
POST /api/v1/integrations
Authorization: Bearer <tenant-admin-token>
Content-Type: application/json

{
  "org_bot_id": "<uuid>",
  "platform": "telegram",
  "bot_token": "<from BotFather>",
  "external_username": "adlomidbot",
  "webhook_secret": "<random>"
}
```

پاسخ شامل `id` و `webhook_secret` است.

## setWebhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://YOUR_HOST/api/v1/integrations/telegram/webhook/<INTEGRATION_ID>" \
  -d "secret_token=<WEBHOOK_SECRET>" \
  -d "allowed_updates=[\"message\",\"callback_query\"]"
```

## ورود با شماره موبایل (OTP پیامکی)

فقط شماره‌های **allowlist** هر بات SMS می‌گیرند (پترن ملّی‌پیامک ورود Liquidglass، bodyId `477732`).

1. در داشبورد `/bots` شماره را به بات اضافه کنید (`POST /api/v1/org-bots/{id}/phones`)
2. env: `SMS_CONSOLE_API_TOKEN` + `SMS_PROVIDER_MODE=real` (لوکال: `stub`)
3. در تلگرام: `/start` → «اشتراک شماره موبایل» → کد پیامک → ارسال کد
4. پشتیبان: «ورود با کد ادمین» یا `/login کد`

وب عمومی: `POST /api/v1/public/bots/{slug}/otp/request` با `{ "phone": "09…" }` سپس login با همان کد.

## صدور OTP ادمین (بدون SMS)

از داشبورد `/bots` یا:

```http
POST /api/v1/org-bots/{bot_id}/otp
```

کد را **خارج از چت عمومی** به مخاطب بدهید. مخاطب در تلگرام می‌نویسد:

```text
/login 123456
```

## امنیت

- توکن را هرگز در git/چت commit نکنید
- اگر توکن افشا شد: BotFather → Revoke و integration را با توکن جدید بسازید
- یک `TELEGRAM_BOT_TOKEN` سراسری برای همهٔ tenantها ممنوع است؛ فقط seed/dev

## Docker / production

- استک کامل: [deployment.fa.md](./deployment.fa.md) (`stack-up` یا `chabokan-stack-up`)
- API باید از اینترنت با HTTPS به مسیر webhook برسد (یا از long-poll bridge بالا)
- Worker باید بالا باشد تا آپدیت‌های enqueueشده (`job_telegram_update`) پردازش شوند
- bootstrap کمکی: `scripts/bootstrap_adl_omid_telegram.py` · OTP: `scripts/issue_telegram_otp.py`

## جریان کاربر نهایی

```text
/start
→ اشتراک شماره موبایل  (یا کد ادمین)
→ کد پیامک / کد ادمین
سؤال آزاد  → پاسخ فقط از KB
وضعیت / خروج
```
