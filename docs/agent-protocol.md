# SSE events — `/api/v1/generate/stream`

**English** | [فارسی](agent-protocol.fa.md)

| Event | Data |
|-------|------|
| `context` | `{ files, truncated }` |
| `message_start` | `{}` |
| `message_delta` | `{ delta }` |
| `message_done` | `{ message }` |
| `edits_generating` | `{}` |
| `result` | AgentResponse JSON |
| `done` | `{ request_id }` |
| `error` | `{ code, message }` |

Reconnect: `GET /api/v1/generate/stream/{request_id}?from={stream_id}`
