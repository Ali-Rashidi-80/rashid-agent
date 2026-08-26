# راهنمای اتصال بله به رشید (فاز D2)

[English](bale.md) | **فارسی**

بله API سازگار با تلگرام دارد: `https://tapi.bale.ai/bot{TOKEN}/...`

## Endpoint رشید

`POST /api/v1/integrations/bale/webhook/{integration_id}`

هدر secret (یکی از این دو):

- `X-Telegram-Bot-Api-Secret-Token`
- `X-Bale-Bot-Api-Secret-Token`

## ساخت integration

همان `POST /api/v1/integrations` با:

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

## رفتار

همان دروازهٔ تلگرام:

- `/login <کد>` → allowlist `chat_id`
- سؤال‌ها فقط Ask + RAG روی KB همان `org_bot`
- idempotency با `processed_messenger_updates`

جزئیات امنیتی و OTP: [telegram.fa.md](./telegram.fa.md)  
استقرار HTTPS و Docker: [deployment.fa.md](./deployment.fa.md)
