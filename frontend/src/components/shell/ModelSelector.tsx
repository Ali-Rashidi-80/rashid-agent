"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";
import { fetchMetisModels } from "@/lib/session-api";
import { useAgentStore } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

export function ModelSelector() {
  const t = useTranslations("topBar");
  const model = useAgentStore((s) => s.model);
  const setModel = useAgentStore((s) => s.setModel);
  const [models, setModels] = useState<string[]>([model]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchMetisModels().then((result) => {
      if (cancelled) {
        return;
      }
      setModels(result.models);
      if (!result.models.includes(model)) {
        setModel(result.default);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [model, setModel]);

  return (
    <div className="relative hidden lg:block">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "inline-flex max-w-[220px] items-center gap-1.5 rounded-lg border border-border bg-background/60 px-3 py-1.5 text-xs",
          "text-foreground hover:bg-muted",
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={t("modelHint")}
      >
        <span className="truncate">
          <span className="text-muted-foreground">{t("model")}: </span>
          {model}
        </span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-70" />
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Close"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setOpen(false)}
          />
          <ul
            role="listbox"
            className="absolute end-0 z-50 mt-1 max-h-64 w-64 overflow-y-auto rounded-lg border border-border bg-card py-1 shadow-xl"
          >
            {models.map((item) => (
              <li key={item}>
                <button
                  type="button"
                  role="option"
                  aria-selected={item === model}
                  onClick={() => {
                    setModel(item);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full px-3 py-2 text-start text-xs transition",
                    item === model
                      ? "bg-primary/15 text-primary"
                      : "text-foreground hover:bg-muted",
                  )}
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
