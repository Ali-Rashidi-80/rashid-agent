import type { AgentMode, AgentResult, ChatTurn } from "./agent-store";

const API_PREFIX = "/api/v1";

export interface ChatSession {
  id: string;
  project_path: string;
  title: string | null;
  mode: string;
  updated_at?: string | null;
}

export interface SessionMessage {
  id: string;
  role: string;
  content: string;
}

export interface PipRunResult {
  ok: boolean;
  stdout?: string;
  stderr?: string;
  error?: string;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string }; detail?: string };
    if (body.error?.message) {
      return body.error.message;
    }
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // ignore JSON parse errors
  }
  return `Request failed (${response.status})`;
}

export async function fetchProjectPath(): Promise<string | null> {
  try {
    const response = await fetch(`${API_PREFIX}/project/path`, { cache: "no-store" });
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as { path?: string };
    return typeof data.path === "string" && data.path.trim() ? data.path : null;
  } catch {
    return null;
  }
}

export async function saveProjectPath(path: string): Promise<string> {
  const response = await fetch(`${API_PREFIX}/project/path`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const data = (await response.json()) as { path?: string };
  if (!data.path) {
    throw new Error("Invalid project path response");
  }
  return data.path;
}

export async function listSessions(projectPath?: string): Promise<ChatSession[]> {
  const query = projectPath ? `?project_path=${encodeURIComponent(projectPath)}` : "";
  try {
    const response = await fetch(`${API_PREFIX}/sessions${query}`, { cache: "no-store" });
    if (!response.ok) {
      return [];
    }
    const data = (await response.json()) as ChatSession[];
    return Array.isArray(data) ? data.filter((s) => s.project_path) : [];
  } catch {
    return [];
  }
}

export async function createSession(
  projectPath: string,
  mode: AgentMode,
  title?: string,
): Promise<ChatSession> {
  const response = await fetch(`${API_PREFIX}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_path: projectPath,
      mode,
      title: title ?? mode,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ChatSession;
}

export function titleFromPrompt(prompt: string, mode: AgentMode): string {
  const cleaned = prompt.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return mode;
  }
  return cleaned.length > 48 ? `${cleaned.slice(0, 48)}…` : cleaned;
}

export async function ensureChatSession(
  projectPath: string,
  mode: AgentMode,
  sessionId: string | null,
  title?: string,
): Promise<string> {
  if (sessionId) {
    try {
      const response = await fetch(`${API_PREFIX}/sessions/${sessionId}`, { cache: "no-store" });
      if (response.ok) {
        const session = (await response.json()) as ChatSession;
        if (session.project_path === projectPath) {
          return session.id;
        }
      }
    } catch {
      // fall through to create
    }
  }
  const created = await createSession(projectPath, mode, title ?? mode);
  return created.id;
}

export function extractAssistantText(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return "";
  }
  try {
    const parsed = JSON.parse(trimmed) as {
      message?: unknown;
      partial?: unknown;
      error?: unknown;
    };
    if (typeof parsed.message === "string" && parsed.message.trim()) {
      return parsed.message;
    }
    if (typeof parsed.partial === "string" && parsed.partial.trim()) {
      return parsed.partial;
    }
    if (typeof parsed.error === "string" && parsed.error.trim()) {
      return parsed.error;
    }
  } catch {
    // plain text fallback
  }
  return trimmed;
}

export function extractAssistantResult(raw: string): AgentResult | null {
  try {
    const parsed = JSON.parse(raw) as Partial<AgentResult>;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return {
      message: typeof parsed.message === "string" ? parsed.message : extractAssistantText(raw),
      pip: typeof parsed.pip === "string" ? parsed.pip : "",
      log: typeof parsed.log === "string" ? parsed.log : "",
      edits: Array.isArray(parsed.edits) ? (parsed.edits as AgentResult["edits"]) : [],
    };
  } catch {
    return null;
  }
}

export async function fetchSessionMessages(sessionId: string): Promise<{
  turns: ChatTurn[];
  lastResult: AgentResult | null;
}> {
  const response = await fetch(`${API_PREFIX}/sessions/${sessionId}/messages`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const data = (await response.json()) as SessionMessage[];
  if (!Array.isArray(data)) {
    return { turns: [], lastResult: null };
  }

  let lastResult: AgentResult | null = null;
  const turns: ChatTurn[] = [];
  for (const item of data) {
    if (item.role !== "user" && item.role !== "assistant") {
      continue;
    }
    if (item.role === "assistant") {
      const parsed = extractAssistantResult(item.content);
      if (parsed) {
        lastResult = parsed;
      }
      turns.push({
        id: item.id,
        role: "assistant",
        content: extractAssistantText(item.content),
      });
    } else {
      turns.push({ id: item.id, role: "user", content: item.content });
    }
  }
  return { turns, lastResult };
}

export async function fetchSession(sessionId: string): Promise<ChatSession | null> {
  try {
    const response = await fetch(`${API_PREFIX}/sessions/${sessionId}`, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as ChatSession;
  } catch {
    return null;
  }
}

export interface MetisProviderCatalog {
  id: string;
  label: string;
  models: string[];
}

export interface MetisModelsCatalog {
  providers: MetisProviderCatalog[];
  default_provider: string;
  default_model: string;
  /** Flat list kept for backward compatibility. */
  models: string[];
  default: string;
}

const FALLBACK_CATALOG: MetisModelsCatalog = {
  providers: [{ id: "grok", label: "Grok / xAI", models: ["grok-code-fast-1"] }],
  default_provider: "grok",
  default_model: "grok-code-fast-1",
  models: ["grok-code-fast-1"],
  default: "grok-code-fast-1",
};

export async function fetchMetisModels(): Promise<MetisModelsCatalog> {
  try {
    const response = await fetch(`${API_PREFIX}/models`, { cache: "no-store" });
    if (!response.ok) {
      return FALLBACK_CATALOG;
    }
    const data = (await response.json()) as Partial<MetisModelsCatalog> & {
      models?: string[];
      default?: string;
    };
    const providers = Array.isArray(data.providers)
      ? data.providers
          .filter((row) => row && typeof row.id === "string")
          .map((row) => ({
            id: row.id,
            label: typeof row.label === "string" && row.label ? row.label : row.id,
            models: Array.isArray(row.models) ? row.models.filter(Boolean) : [],
          }))
          .filter((row) => row.models.length > 0)
      : [];
    const default_provider =
      typeof data.default_provider === "string" && data.default_provider
        ? data.default_provider
        : providers[0]?.id || FALLBACK_CATALOG.default_provider;
    const default_model =
      typeof data.default_model === "string" && data.default_model
        ? data.default_model
        : typeof data.default === "string" && data.default
          ? data.default
          : FALLBACK_CATALOG.default_model;
    const flat = Array.isArray(data.models) ? data.models.filter(Boolean) : [];
    const models =
      flat.length > 0
        ? flat
        : providers.flatMap((p) => p.models).length
          ? providers.flatMap((p) => p.models)
          : [default_model];
    return {
      providers: providers.length ? providers : FALLBACK_CATALOG.providers,
      default_provider,
      default_model,
      models,
      default: default_model,
    };
  } catch {
    return FALLBACK_CATALOG;
  }
}

export async function runPipCommand(command: string): Promise<PipRunResult> {
  const response = await fetch(`${API_PREFIX}/pip/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  });
  const data = (await response.json()) as PipRunResult;
  if (!response.ok && !data.error) {
    data.error = await parseError(response);
    data.ok = false;
  }
  return data;
}
