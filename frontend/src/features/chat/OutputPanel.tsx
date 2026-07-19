"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { useTranslations } from "next-intl";
import { Loader2, Terminal } from "lucide-react";
import { useAgentStore, type ChatTurn } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface OutputPanelProps {
  content: string;
  isStreaming: boolean;
  error: string | null;
  phase?: string;
  agentLog?: string;
  pipCommand?: string;
  onRunPip?: (command: string) => void | Promise<void>;
  pipRunning?: boolean;
}

function TurnBubble({
  turn,
  userLabel,
  assistantLabel,
}: {
  turn: ChatTurn;
  userLabel: string;
  assistantLabel: string;
}) {
  const isUser = turn.role === "user";
  return (
    <div
      className={cn(
        "rounded-lg px-3 py-2 text-sm",
        isUser
          ? "ms-6 border border-border bg-muted/50 text-foreground"
          : "me-4 bg-transparent",
      )}
    >
      <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        {isUser ? userLabel : assistantLabel}
      </p>
      {isUser ? (
        <p className="whitespace-pre-wrap">{turn.content}</p>
      ) : (
        <div className="markdown-output">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {turn.content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export function OutputPanel({
  content,
  isStreaming,
  error,
  phase,
  agentLog,
  pipCommand,
  onRunPip,
  pipRunning = false,
}: OutputPanelProps) {
  const t = useTranslations("chat");
  const transcript = useAgentStore((s) => s.transcript);
  const mode = useAgentStore((s) => s.mode);
  const hasHistory = transcript.length > 0;
  const showLive = isStreaming && Boolean(content);

  return (
    <section className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-medium">{t("outputTitle")}</h2>
          <span
            className={cn(
              "rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase",
              mode === "ask" && "bg-sky-500/20 text-sky-300",
              mode === "plan" && "bg-amber-500/20 text-amber-300",
              mode === "agent" && "bg-emerald-500/20 text-emerald-300",
            )}
          >
            {mode}
          </span>
        </div>
        {isStreaming && (
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t("streaming")}
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {error && (
          <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error}
          </p>
        )}

        {phase === "edits" && isStreaming && (
          <p className="text-xs text-muted-foreground">{t("generatingEdits")}</p>
        )}

        {agentLog && (
          <pre className="overflow-x-auto rounded-lg border border-border bg-muted/40 p-2 text-xs">
            {agentLog}
          </pre>
        )}

        {pipCommand && onRunPip && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs">
            <code className="flex-1 break-all text-amber-200">{pipCommand}</code>
            <button
              type="button"
              disabled={pipRunning}
              onClick={() => void onRunPip(pipCommand)}
              className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 px-2 py-1 font-medium text-amber-100 hover:bg-amber-500/20 disabled:opacity-50"
            >
              {pipRunning ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Terminal className="h-3.5 w-3.5" />
              )}
              {t("runPip")}
            </button>
          </div>
        )}

        {!hasHistory && !showLive && !error && (
          <p className="text-sm text-muted-foreground">{t("emptyOutput")}</p>
        )}

        {transcript.map((turn) => (
          <TurnBubble
            key={turn.id}
            turn={turn}
            userLabel={t("roleUser")}
            assistantLabel={t("roleAssistant")}
          />
        ))}

        {showLive && (
          <div className="me-4 rounded-lg px-3 py-2 text-sm">
            <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
              {t("roleAssistant")}
            </p>
            <div className={cn("markdown-output", "opacity-90")}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                {content}
              </ReactMarkdown>
              <span className="ms-1 inline-block h-4 w-0.5 animate-pulse bg-primary" />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
