const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function forwardRequestHeaders(request: Request): Headers {
  const headers = new Headers();

  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const apiToken = process.env.RASHID_TOKEN?.trim();
  if (apiToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${apiToken}`);
  }

  headers.set("Accept", "text/event-stream");

  return headers;
}

export async function POST(request: Request) {
  const target = `${BACKEND_URL}/api/v1/generate/stream`;

  const backendResponse = await fetch(target, {
    method: "POST",
    headers: forwardRequestHeaders(request),
    body: request.body,
    // @ts-expect-error Node fetch requires duplex for streaming request bodies
    duplex: "half",
  });

  const headers = new Headers();
  headers.set("Content-Type", "text/event-stream; charset=utf-8");
  headers.set("Cache-Control", "no-cache, no-transform");
  headers.set("Connection", "keep-alive");
  headers.set("X-Accel-Buffering", "no");

  backendResponse.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers,
  });
}

export async function GET() {
  return new Response("SSE endpoint expects POST", { status: 405 });
}
