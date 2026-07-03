"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Activity, Circle, FolderOpen } from "lucide-react";
import { useAgentStore } from "@/lib/agent-store";

export function StatusBar() {
  const t = useTranslations("statusBar");
  const phase = useAgentStore((s) => s.phase);
  const [connected, setConnected] = useState(false);
  const [projectPath, setProjectPath] = useState("—");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const response = await fetch("/api/v1/health");
        if (!cancelled) {
          setConnected(response.ok);
        }
      } catch {
        if (!cancelled) {
          setConnected(false);
        }
      }
    }

    async function loadPath() {
      try {
        const response = await fetch("/api/v1/project/path");
        if (!cancelled && response.ok) {
          const data = (await response.json()) as { path?: string };
          setProjectPath(data.path ?? "—");
        }
      } catch {
        if (!cancelled) {
          setProjectPath("—");
        }
      }
    }

    checkHealth();
    loadPath();
    const interval = window.setInterval(checkHealth, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const phaseLabel =
    phase === "idle"
      ? t("idle")
      : phase === "message"
        ? t("phaseMessage")
        : phase === "edits"
          ? t("phaseEdits")
          : phase === "done"
            ? t("phaseDone")
            : phase === "error"
              ? t("phaseError")
              : t("idle");

  return (
    <footer className="flex h-8 shrink-0 items-center gap-4 border-t border-border bg-sidebar px-4 text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <Circle
          className={`h-2 w-2 fill-current ${connected ? "text-emerald-500" : "text-red-500"}`}
        />
        {connected ? t("connected") : t("disconnected")}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Activity className="h-3 w-3" />
        {t("phase")}: {phaseLabel}
      </span>
      <span className="inline-flex items-center gap-1.5 truncate">
        <FolderOpen className="h-3 w-3 shrink-0" />
        {t("path")}: {projectPath}
      </span>
    </footer>
  );
}
