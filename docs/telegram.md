# Telegram integration — Rashid Agent (Phase D)

**English** | [فارسی](telegram.fa.md)

## Architecture

Each Telegram bot = one `messenger_integrations` row → one `org_bot` → one `knowledge_base` → one `tenant`.

- Webhook: `POST /api/v1/integrations/telegram/webhook/{integration_id}`
- Required header: `X-Telegram-Bot-Api-Secret-Token` (timing-safe compare with `webhook_secret`)
- Bot token encrypted in DB (`SECRETS_ENCRYPTION_KEY`)
- Commands: `/start` `/help` `/login <code>` `/logout` `/status`
- After successful `/login`, `chat_id` is stored in `messenger_links`
- Questions are Ask + RAG only on that `org_bot` KB

## Prerequisites

1. Phase B (KB) and C (org_bot + OTP) ready
2. `SECRETS_ENCRYPTION_KEY` in `.env` (long random string)
3. Public HTTPS for webhook (or a tunnel). If the tunnel times out from your network, for local dev:

```bash
python scripts/telegram_longpoll_bridge.py
```

This script calls `deleteWebhook` and forwards `getUpdates` to the local webhook — same `X-Telegram-Bot-Api-Secret-Token` header.

For the mirror stack (`rashid-mirror-*` on `:8001`):

```bash
python scripts/bootstrap_mirror_telegram.py
python scripts/telegram_longpoll_bridge.py
```

`api_base` is read from the bootstrap summary file (`http://127.0.0.1:8001`).

## Professional bot profile texts

Apply name, short description, full description (“What can this bot do?”), and command list via API:

```bash
python scripts/apply_telegram_bot_profile.py
```

JSON output in `backend/data/telegram_botfather_paste.json` includes Mini App / Direct Link texts (those sections are only editable in BotFather).

Source: `backend/app/services/telegram_bot_profile.py`

## Create integration via API

With tenant admin token:

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

Response includes `id` and `webhook_secret`.

## setWebhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://YOUR_HOST/api/v1/integrations/telegram/webhook/<INTEGRATION_ID>" \
  -d "secret_token=<WEBHOOK_SECRET>" \
  -d "allowed_updates=[\"message\",\"callback_query\"]"
```

## Phone login (SMS OTP)

Only **allowlisted** phones per bot receive SMS (MeliPayamak Liquidglass login pattern, bodyId `477732`).

1. Add the number on the bot in `/bots` (`POST /api/v1/org-bots/{id}/phones`)
2. Env: `SMS_CONSOLE_API_TOKEN` + `SMS_PROVIDER_MODE=real` (local: `stub`)
3. In Telegram: `/start` → share mobile → SMS code → send code
4. Fallback: admin code login or `/login <code>`

Public web: `POST /api/v1/public/bots/{slug}/otp/request` with `{ "phone": "09…" }` then login with the same code.

## Admin OTP (no SMS)

From `/bots` or:

```http
POST /api/v1/org-bots/{bot_id}/otp
```

Give the code **outside** the public chat. Contact types in Telegram:

```text
/login 123456
```

## Security

- Never commit tokens to git/chat
- If leaked: BotFather → Revoke and recreate integration with a new token
- One global `TELEGRAM_BOT_TOKEN` for all tenants is forbidden; seed/dev only

## Docker / production

- Full stack: [deployment.md](./deployment.md) (`stack-up` or `chabokan-stack-up`)
- API must be reachable from the internet over HTTPS for the webhook path (or use the long-poll bridge)
- Worker must be up for enqueued updates (`job_telegram_update`)
- Helpers: `scripts/bootstrap_adl_omid_telegram.py` · OTP: `scripts/issue_telegram_otp.py`

## End-user flow

```text
/start
→ share mobile  (or admin code)
→ SMS / admin code
free question  → answer from KB only
status / logout
```
