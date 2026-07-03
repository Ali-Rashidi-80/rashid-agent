import type { AgentMode } from "./agent-store";

const API_PREFIX = "/api/v1";

export interface ChatSession {
  id: string;
  project_path: string;
  title: string | null;
  mode: string;
  updated_at?: string | null;
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

export async function ensureChatSession(
  projectPath: string,
  mode: AgentMode,
  sessionId: string | null,
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
  const created = await createSession(projectPath, mode);
  return created.id;
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
