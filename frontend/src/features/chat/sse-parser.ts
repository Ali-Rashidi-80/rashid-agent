export interface SSEParsedEvent {
  event: string;
  data: Record<string, unknown>;
  id?: string;
}

export function parseSSEBlock(block: string): SSEParsedEvent | null {
  const lines = block.split("\n");
  let event = "message";
  let id: string | undefined;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("id:")) {
      id = line.slice(3).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  const dataLine = dataLines.join("\n");
  if (!dataLine || dataLine === "[DONE]") {
    return null;
  }

  try {
    const data = JSON.parse(dataLine) as Record<string, unknown>;
    return id ? { event, data, id } : { event, data };
  } catch {
    return id ? { event, data: { text: dataLine }, id } : { event, data: { text: dataLine } };
  }
}

export function reduceSSEContent(
  previous: string,
  event: SSEParsedEvent,
): { content: string; error: string | null } {
  const { event: type, data } = event;

  if (
    type === "heartbeat" ||
    type === "context" ||
    type === "message_start" ||
    type === "edits_generating" ||
    type === "done"
  ) {
    return { content: previous, error: null };
  }

  if (type === "error") {
    const message =
      typeof data.message === "string"
        ? data.message
        : typeof data.code === "string"
          ? data.code
          : "Stream error";
    return { content: previous, error: message };
  }

  if (type === "message_delta") {
    const delta =
      typeof data.delta === "string"
        ? data.delta
        : typeof data.content === "string"
          ? data.content
          : typeof data.text === "string"
            ? data.text
            : "";
    return { content: previous + delta, error: null };
  }

  if (type === "message_done" || type === "result") {
    const message = typeof data.message === "string" ? data.message : previous;
    return { content: message, error: null };
  }

  const fallback =
    typeof data.delta === "string"
      ? data.delta
      : typeof data.content === "string"
        ? data.content
        : typeof data.message === "string"
          ? data.message
          : "";

  if (fallback) {
    return { content: previous + fallback, error: null };
  }

  return { content: previous, error: null };
}
