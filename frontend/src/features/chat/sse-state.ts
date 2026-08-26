import type { AgentResult, StreamPhase } from "@/lib/agent-store";
import type { SSEParsedEvent } from "./sse-parser";

export interface RagSource {
  filename: string;
  excerpt: string;
  score: number;
}

export interface SSEStreamState {
  content: string;
  error: string | null;
  warnings: string[];
  phase: StreamPhase;
  result: AgentResult | null;
  requestId: string | null;
  sources: RagSource[];
}

export const initialSSEState: SSEStreamState = {
  content: "",
  error: null,
  warnings: [],
  phase: "idle",
  result: null,
  requestId: null,
  sources: [],
};

function parseAgentResult(data: Record<string, unknown>): AgentResult {
  const edits = Array.isArray(data.edits) ? data.edits : [];
  return {
    message: typeof data.message === "string" ? data.message : "",
    pip: typeof data.pip === "string" ? data.pip : "",
    log: typeof data.log === "string" ? data.log : "",
    edits: edits
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        path: typeof item.path === "string" ? item.path : "",
        edits: Array.isArray(item.edits)
          ? item.edits
              .filter((e): e is Record<string, unknown> => typeof e === "object" && e !== null)
              .map((e) => ({
                start_number_line: Number(e.start_number_line ?? 1),
                end_number_line: Number(e.end_number_line ?? 1),
                code: typeof e.code === "string" ? e.code : "",
                new_code: typeof e.new_code === "string" ? e.new_code : "",
              }))
          : [],
      }))
      .filter((f) => f.path),
  };
}

export function reduceSSEState(
  previous: SSEStreamState,
  event: SSEParsedEvent,
): SSEStreamState {
  const { event: type, data } = event;
  const next = { ...previous };

  if (type === "context") {
    next.requestId = typeof data.request_id === "string" ? data.request_id : previous.requestId;
    return next;
  }

  if (type === "sources") {
    const rows = Array.isArray(data.sources) ? data.sources : [];
    next.sources = rows
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        filename: typeof item.filename === "string" ? item.filename : "document",
        excerpt: typeof item.excerpt === "string" ? item.excerpt : "",
        score: typeof item.score === "number" ? item.score : 0,
      }));
    return next;
  }

  if (type === "message_start") {
    next.phase = "message";
    return next;
  }

  if (type === "edits_generating") {
    next.phase = "edits";
    return next;
  }

  if (type === "heartbeat") {
    return next;
  }

  if (type === "reconnect_degraded") {
    const message =
      typeof data.message === "string" ? data.message : "Reconnect replay unavailable";
    if (!next.warnings.includes(message)) {
      next.warnings = [...next.warnings, message];
    }
    return next;
  }

  if (type === "verify") {
    if (data.ok === false && Array.isArray(data.issues)) {
      for (const issue of data.issues) {
        if (typeof issue === "string" && !next.warnings.includes(issue)) {
          next.warnings = [...next.warnings, issue];
        }
      }
    }
    return next;
  }

  if (type === "error") {
    next.error =
      typeof data.message === "string"
        ? data.message
        : typeof data.code === "string"
          ? data.code
          : "Stream error";
    next.phase = "error";
    return next;
  }

  if (type === "message_delta") {
    const delta =
      typeof data.delta === "string"
        ? data.delta
        : typeof data.content === "string"
          ? data.content
          : "";
    next.content = previous.content + delta;
    next.phase = "message";
    return next;
  }

  if (type === "message_done") {
    next.content = typeof data.message === "string" ? data.message : previous.content;
    return next;
  }

  if (type === "result") {
    next.result = parseAgentResult(data);
    next.content = next.result.message || previous.content;
    next.phase = "done";
    return next;
  }

  if (type === "done") {
    if (data.cancelled === true || data.incomplete === true) {
      if (!previous.error) {
        next.error =
          typeof data.message === "string" ? data.message : "Stream ended incomplete";
      }
      next.phase = "error";
    } else if (previous.result) {
      next.phase = "done";
    }
    return next;
  }

  return next;
}
