"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useAgentStore, type AgentMode } from "@/lib/agent-store";
import {
  fetchProjectPath,
  fetchSession,
  fetchSessionMessages,
  listSessions,
  type ChatSession,
} from "@/lib/session-api";
import { cn } from "@/lib/cn";

interface SessionHistoryProps {
  onSelectSession?: () => void;
  refreshToken?: number;
}

function isAgentMode(value: string): value is AgentMode {
  return value === "ask" || value === "plan" || value === "agent";
}

export function SessionHistory({ onSelectSession, refreshToken = 0 }: SessionHistoryProps) {
  const t = useTranslations("nav");
  const sessionId = useAgentStore((s) => s.sessionId);
  const setSessionId = useAgentStore((s) => s.setSessionId);
  const setMode = useAgentStore((s) => s.setMode);
  const setTranscript = useAgentStore((s) => s.setTranscript);
  const setRestoredResult = useAgentStore((s) => s.setRestoredResult);
  const bumpChatEpoch = useAgentStore((s) => s.bumpChatEpoch);
  const setPhase = useAgentStore((s) => s.setPhase);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [projectPath, setProjectPath] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    void fetchProjectPath().then(setProjectPath);
  }, []);

  const load = useCallback(async () => {
    const path = projectPath ?? (await fetchProjectPath());
    if (path && path !== projectPath) {
      setProjectPath(path);
    }
    const items = await listSessions(path ?? undefined);
    setSessions(items.slice(0, 24));
  }, [projectPath]);

  useEffect(() => {
    void load();
    const interval = window.setInterval(load, 15000);
    return () => window.clearInterval(interval);
  }, [load, refreshToken]);

  const openSession = async (session: ChatSession) => {
    if (loadingId) {
      return;
    }
    setLoadingId(session.id);
    try {
      const detail = (await fetchSession(session.id)) ?? session;
      const { turns, lastResult } = await fetchSessionMessages(session.id);
      setSessionId(detail.id);
      if (isAgentMode(detail.mode)) {
        setMode(detail.mode);
      }
      setTranscript(turns);
      setRestoredResult(lastResult);
      setPhase(turns.length ? "done" : "idle");
      bumpChatEpoch();
      onSelectSession?.();
      toast.success(t("sessionOpened"));
    } catch (err) {
      toast.error((err as Error).message || t("sessionOpenFailed"));
    } finally {
      setLoadingId(null);
    }
  };

  if (sessions.length === 0) {
    return (
      <p className="px-3 py-2 text-xs text-muted-foreground">{t("noSessions")}</p>
    );
  }

  return (
    <ul className="flex flex-col gap-1 px-2">
      {sessions.map((session) => {
        const title = session.title?.trim() || session.mode;
        const active = sessionId === session.id;
        return (
          <li key={session.id}>
            <button
              type="button"
              disabled={loadingId === session.id}
              onClick={() => void openSession(session)}
              className={cn(
                "w-full rounded-lg px-3 py-2 text-start text-xs transition disabled:opacity-60",
                active
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <span className="block truncate font-medium">{title}</span>
              <span className="block truncate opacity-70" dir="ltr">
                {session.project_path}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
