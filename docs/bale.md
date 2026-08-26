# Bale integration — Rashid Agent (Phase D2)

**English** | [فارسی](bale.fa.md)

Bale exposes a Telegram-compatible API: `https://tapi.bale.ai/bot{TOKEN}/...`

## Rashid endpoint

`POST /api/v1/integrations/bale/webhook/{integration_id}`

Secret header (either):

- `X-Telegram-Bot-Api-Secret-Token`
- `X-Bale-Bot-Api-Secret-Token`

## Create integration

Same `POST /api/v1/integrations` with:

```json
{
  "org_bot_id": "<uuid>",
  "platform": "bale",
  "bot_token": "<TOKEN>",
  "external_username": "mybalebot",
  "webhook_secret": "<random>"
}
```

## setWebhook

```bash
curl "https://tapi.bale.ai/bot<TOKEN>/setWebhook" \
  -d "url=https://YOUR_HOST/api/v1/integrations/bale/webhook/<INTEGRATION_ID>" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

## Behavior

Same gateway as Telegram:

- `/login <code>` → allowlist `chat_id`
- Questions are Ask + RAG on that `org_bot` KB only
- Idempotency via `processed_messenger_updates`

Security and OTP details: [telegram.md](./telegram.md)  
HTTPS and Docker: [deployment.md](./deployment.md)
