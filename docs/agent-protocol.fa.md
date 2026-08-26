# رویدادهای SSE — `/api/v1/generate/stream`

[English](agent-protocol.md) | **فارسی**

| رویداد | داده |
|--------|------|
| `context` | `{ files, truncated }` |
| `message_start` | `{}` |
| `message_delta` | `{ delta }` |
| `message_done` | `{ message }` |
| `edits_generating` | `{}` |
| `result` | JSON مربوط به AgentResponse |
| `done` | `{ request_id }` |
| `error` | `{ code, message }` |

اتصال مجدد: `GET /api/v1/generate/stream/{request_id}?from={stream_id}`
