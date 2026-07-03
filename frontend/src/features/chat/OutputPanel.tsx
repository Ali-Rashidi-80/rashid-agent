"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { useTranslations } from "next-intl";
import { Loader2, Terminal } from "lucide-react";
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

  return (
    <section className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-medium">{t("outputTitle")}</h2>
        {isStreaming && (
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t("streaming")}
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {error && (
          <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error}
          </p>
        )}

        {phase === "edits" && isStreaming && (
          <p className="mb-3 text-xs text-muted-foreground">{t("generatingEdits")}</p>
        )}

        {agentLog && (
          <pre className="mb-3 overflow-x-auto rounded-lg border border-border bg-muted/40 p-2 text-xs">
            {agentLog}
          </pre>
        )}

        {pipCommand && onRunPip && (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs">
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

        {!content && !error && (
          <p className="text-sm text-muted-foreground">{t("emptyOutput")}</p>
        )}

        {content && (
          <div className={cn("markdown-output", isStreaming && "opacity-90")}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="ms-1 inline-block h-4 w-0.5 animate-pulse bg-primary" />
            )}
          </div>
        )}
      </div>
    </section>
  );
}
