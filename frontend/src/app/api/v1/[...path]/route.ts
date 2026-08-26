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

function buildTargetUrl(path: string[], search: string) {
  const suffix = path.length > 0 ? `/${path.join("/")}` : "";
  return `${BACKEND_URL}/api/v1${suffix}${search}`;
}

function forwardRequestHeaders(request: Request, path: string[]): Headers {
  const headers = new Headers();

  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  // Public bot gate uses its own session bearer — never inject platform token.
  const isPublic = path[0] === "public";
  const apiToken = process.env.RASHID_TOKEN?.trim();
  if (!isPublic && apiToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${apiToken}`);
  }

  return headers;
}

function forwardResponseHeaders(response: Response): Headers {
  const headers = new Headers();

  response.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  return headers;
}

async function proxyRequest(request: Request, path: string[]) {
  const url = new URL(request.url);
  const target = buildTargetUrl(path, url.search);
  const method = request.method.toUpperCase();
  const init: RequestInit = {
    method,
    headers: forwardRequestHeaders(request, path),
    redirect: "manual",
  };

  if (method !== "GET" && method !== "HEAD") {
    if (request.body) {
      init.body = request.body;
      // @ts-expect-error Node fetch requires duplex for streaming request bodies
      init.duplex = "half";
    }
  }

  const response = await fetch(target, init);

  const headers = forwardResponseHeaders(response);
  if (response.headers.get("content-type")?.includes("text/event-stream")) {
    headers.set("Cache-Control", "no-cache, no-transform");
    headers.set("X-Accel-Buffering", "no");
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function OPTIONS(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}
