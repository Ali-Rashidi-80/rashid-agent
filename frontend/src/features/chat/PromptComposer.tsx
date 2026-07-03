"use client";

import { useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Loader2, Send, Square } from "lucide-react";
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
    <div className="glass-panel sticky top-0 z-10 p-3">
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
            disabled={!value.trim()}
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
