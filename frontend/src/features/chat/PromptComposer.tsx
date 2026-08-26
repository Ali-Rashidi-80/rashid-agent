"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2, Send, Square } from "lucide-react";
import { listKnowledgeBases, type KnowledgeBase } from "@/lib/knowledge-api";
import { readTenantAuth } from "@/lib/tenant-auth";
import { useAgentStore } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface PromptComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  isStreaming: boolean;
}

export function PromptComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  isStreaming,
}: PromptComposerProps) {
  const t = useTranslations("chat");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const knowledgeBaseId = useAgentStore((s) => s.knowledgeBaseId);
  const ragOnly = useAgentStore((s) => s.ragOnly);
  const setKnowledgeBaseId = useAgentStore((s) => s.setKnowledgeBaseId);
  const setRagOnly = useAgentStore((s) => s.setRagOnly);
  const [bases, setBases] = useState<KnowledgeBase[]>([]);

  useEffect(() => {
    if (!readTenantAuth()) {
      setBases([]);
      return;
    }
    let cancelled = false;
    void listKnowledgeBases()
      .then((rows) => {
        if (!cancelled) {
          setBases(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBases([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  };

  const autoResize = useCallback(() => {
    const element = textareaRef.current;
    if (!element) {
      return;
    }
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`;
  }, []);

  return (
    <div className="glass-panel sticky top-0 z-10 space-y-2 p-3">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="inline-flex items-center gap-1.5 text-muted-foreground">
          <input
            type="checkbox"
            checked={ragOnly}
            onChange={(event) => setRagOnly(event.target.checked)}
            disabled={isStreaming}
            className="rounded border-border"
          />
          {t("ragOnly")}
        </label>
        <label className="inline-flex items-center gap-1.5 text-muted-foreground">
          <span>{t("knowledgeBase")}</span>
          <select
            value={knowledgeBaseId ?? ""}
            onChange={(event) => setKnowledgeBaseId(event.target.value || null)}
            disabled={isStreaming}
            className="max-w-[220px] rounded-md border border-border bg-background px-2 py-1 text-foreground"
          >
            <option value="">{t("noKnowledgeBase")}</option>
            {bases.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </label>
        {ragOnly && !knowledgeBaseId ? (
          <span className="text-amber-700 dark:text-amber-300">{t("ragNeedsKb")}</span>
        ) : null}
      </div>

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          rows={2}
          disabled={isStreaming}
          className={cn(
            "min-h-[72px] flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm",
            "placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring",
          )}
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-medium text-white"
          >
            <Square className="h-4 w-4" />
            {t("stop")}
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={!value.trim() || (ragOnly && !knowledgeBaseId)}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {t("send")}
          </button>
        )}
      </div>
    </div>
  );
}
