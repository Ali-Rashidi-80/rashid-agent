"use client";

import { useCallback, useRef, useState } from "react";
import { useAgentStore, type AgentResult } from "@/lib/agent-store";
import { ensureChatSession, fetchProjectPath, titleFromPrompt } from "@/lib/session-api";
import { parseSSEBlock } from "./sse-parser";
import { initialSSEState, reduceSSEState, type SSEStreamState } from "./sse-state";

export interface SSEStreamPayload {
  prompt: string;
  mode?: string;
  session_id?: string | null;
  [key: string]: unknown;
}

export interface UseSSEResult {
  content: string;
  isStreaming: boolean;
  error: string | null;
  phase: SSEStreamState["phase"];
  result: AgentResult | null;
  start: (payload: SSEStreamPayload) => Promise<void>;
  stop: () => void;
  reset: () => void;
}

export const RECONNECT_DELAYS_MS = [1000, 2000, 4000] as const;
export const RECONNECT_ATTEMPTS = RECONNECT_DELAYS_MS.length + 1;

export async function sleepMs(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

export function isStreamIncomplete(state: SSEStreamState): boolean {
  return state.phase !== "done" && state.phase !== "error" && !state.result;
}

interface ConsumeResult {
  state: SSEStreamState;
  lastEventId: string;
}

async function consumeSSEBody(
  body: ReadableStream<Uint8Array>,
  accumulated: SSEStreamState,
  onUpdate: (state: SSEStreamState) => void,
  initialLastEventId = "0",
): Promise<ConsumeResult> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let current = accumulated;
  let lastEventId = initialLastEventId;

  const consumeBlock = (block: string) => {
    const parsed = parseSSEBlock(block);
    if (!parsed) {
      return false;
    }
    if (parsed.id) {
      lastEventId = parsed.id;
    }
    current = reduceSSEState(current, parsed);
    onUpdate(current);
    return parsed.event === "done";
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const block of events) {
      if (consumeBlock(block)) {
        return { state: current, lastEventId };
      }
    }
  }

  if (buffer.trim()) {
    consumeBlock(buffer);
  }

  return { state: current, lastEventId };
}

export function useSSE(endpoint = "/api/v1/generate/stream"): UseSSEResult {
  const mode = useAgentStore((s) => s.mode);
  const model = useAgentStore((s) => s.model);
  const sessionId = useAgentStore((s) => s.sessionId);
  const setSessionId = useAgentStore((s) => s.setSessionId);
  const setPhase = useAgentStore((s) => s.setPhase);
  const appendTurn = useAgentStore((s) => s.appendTurn);

  const [state, setState] = useState<SSEStreamState>(initialSSEState);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef<string | null>(null);
  const lastEventIdRef = useRef<string>("0");
  const stateRef = useRef<SSEStreamState>(initialSSEState);
  stateRef.current = state;

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setPhase("idle");
  }, [setPhase]);

  const reset = useCallback(() => {
    stop();
    setState(initialSSEState);
    requestIdRef.current = null;
    lastEventIdRef.current = "0";
  }, [stop]);

  const start = useCallback(
    async (payload: SSEStreamPayload) => {
      stop();
      setState(initialSSEState);
      setIsStreaming(true);
      setPhase("message");
      requestIdRef.current = null;
      lastEventIdRef.current = "0";

      const controller = new AbortController();
      abortRef.current = controller;

      const onUpdate = (next: SSEStreamState) => {
        if (next.requestId) {
          requestIdRef.current = next.requestId;
        }
        setState(next);
        setPhase(next.phase);
      };

      try {
        const projectPath = await fetchProjectPath();
        if (!projectPath) {
          throw new Error("Project path is not configured");
        }
        const promptText = String(payload.prompt ?? "");
        appendTurn({
          id: `local-user-${Date.now()}`,
          role: "user",
          content: promptText,
        });
        const activeSessionId = await ensureChatSession(
          projectPath,
          mode,
          sessionId,
          titleFromPrompt(promptText, mode),
        );
        if (activeSessionId !== sessionId) {
          setSessionId(activeSessionId);
        }

        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            Accept: "text/event-stream",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...payload,
            mode,
            model,
            session_id: activeSessionId,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Stream failed (${response.status})`);
        }

        if (!response.body) {
          throw new Error("Stream body is empty");
        }

        const headerRequestId = response.headers.get("X-Request-Id");
        if (headerRequestId) {
          requestIdRef.current = headerRequestId;
        }

        const consumed = await consumeSSEBody(response.body, initialSSEState, onUpdate);
        lastEventIdRef.current = consumed.lastEventId;
        if (isStreamIncomplete(consumed.state)) {
          throw new Error("Stream ended before completion");
        }
        if (consumed.state.content.trim()) {
          appendTurn({
            id: `local-assistant-${Date.now()}`,
            role: "assistant",
            content: consumed.state.content,
          });
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          return;
        }

        const reconnectId = requestIdRef.current;
        if (reconnectId && isStreamIncomplete(stateRef.current)) {
          let reconnectedOk = false;
          for (let attempt = 0; attempt < RECONNECT_ATTEMPTS; attempt++) {
            if (attempt > 0) {
              await sleepMs(RECONNECT_DELAYS_MS[attempt - 1]);
            }
            try {
              const fromId = encodeURIComponent(lastEventIdRef.current || "0");
              const reconnect = await fetch(
                `/api/v1/generate/stream/${reconnectId}?from_id=${fromId}`,
                {
                  headers: { Accept: "text/event-stream" },
                  signal: controller.signal,
                },
              );
              if (!reconnect.ok || !reconnect.body) {
                continue;
              }
              const reconnected = await consumeSSEBody(
                reconnect.body,
                stateRef.current,
                onUpdate,
                lastEventIdRef.current,
              );
              lastEventIdRef.current = reconnected.lastEventId;
              if (!isStreamIncomplete(reconnected.state)) {
                reconnectedOk = true;
                break;
              }
            } catch {
              // try next backoff
            }
          }
          if (reconnectedOk) {
            return;
          }
        }

        const message = stateRef.current.error ?? (err as Error).message;
        setState((prev) => ({ ...prev, error: message, phase: "error" }));
        setPhase("error");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [appendTurn, endpoint, mode, model, sessionId, setPhase, setSessionId, stop],
  );

  return {
    content: state.content,
    isStreaming,
    error: state.error,
    phase: state.phase,
    result: state.result,
    start,
    stop,
    reset,
  };
}
