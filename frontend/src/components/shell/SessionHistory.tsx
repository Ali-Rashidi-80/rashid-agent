"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useAgentStore } from "@/lib/agent-store";
import { fetchProjectPath, listSessions, type ChatSession } from "@/lib/session-api";
import { cn } from "@/lib/cn";

export function SessionHistory() {
  const t = useTranslations("nav");
  const sessionId = useAgentStore((s) => s.sessionId);
  const setSessionId = useAgentStore((s) => s.setSessionId);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [projectPath, setProjectPath] = useState<string | null>(null);

  useEffect(() => {
    void fetchProjectPath().then(setProjectPath);
  }, []);

  const load = useCallback(async () => {
    const path = projectPath ?? (await fetchProjectPath());
    if (path && path !== projectPath) {
      setProjectPath(path);
    }
    const items = await listSessions(path ?? undefined);
    setSessions(items.slice(0, 12));
  }, [projectPath]);

  useEffect(() => {
    void load();
    const interval = window.setInterval(load, 20000);
    return () => window.clearInterval(interval);
  }, [load]);

  if (sessions.length === 0) {
    return (
      <p className="px-3 py-2 text-xs text-muted-foreground">{t("noSessions")}</p>
    );
  }

  return (
    <ul className="flex flex-col gap-1 px-2">
      {sessions.map((session) => (
        <li key={session.id}>
          <button
            type="button"
            onClick={() => setSessionId(session.id)}
            className={cn(
              "w-full rounded-lg px-3 py-2 text-start text-xs transition",
              sessionId === session.id
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <span className="block truncate font-medium">
              {session.title ?? session.mode}
            </span>
            <span className="block truncate opacity-70">{session.project_path}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
