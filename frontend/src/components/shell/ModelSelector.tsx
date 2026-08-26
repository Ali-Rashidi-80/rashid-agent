"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";
import { fetchMetisModels, type MetisProviderCatalog } from "@/lib/session-api";
import { useAgentStore } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

export function ModelSelector() {
  const t = useTranslations("topBar");
  const provider = useAgentStore((s) => s.provider);
  const model = useAgentStore((s) => s.model);
  const setProviderModel = useAgentStore((s) => s.setProviderModel);
  const [providers, setProviders] = useState<MetisProviderCatalog[]>([]);
  const [open, setOpen] = useState(false);
  const [modelQuery, setModelQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    void fetchMetisModels().then((result) => {
      if (cancelled) {
        return;
      }
      setProviders(result.providers);
      const current = useAgentStore.getState();
      const active =
        result.providers.find((row) => row.id === current.provider) ??
        result.providers.find((row) => row.id === result.default_provider) ??
        result.providers[0];
      if (!active) {
        return;
      }
      const nextModel = active.models.includes(current.model)
        ? current.model
        : active.models.includes(result.default_model)
          ? result.default_model
          : active.models[0];
      if (active.id !== current.provider || nextModel !== current.model) {
        setProviderModel(active.id, nextModel);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [setProviderModel]);

  const activeProvider = useMemo(
    () => providers.find((row) => row.id === provider) ?? providers[0],
    [provider, providers],
  );
  const models = useMemo(() => {
    const all = activeProvider?.models ?? [model];
    const q = modelQuery.trim().toLowerCase();
    if (!q) {
      return all;
    }
    return all.filter((item) => item.toLowerCase().includes(q));
  }, [activeProvider?.models, model, modelQuery]);

  return (
    <div className="relative max-w-[min(100%,28rem)]">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "inline-flex max-w-[280px] items-center gap-1.5 rounded-lg border border-border bg-background/60 px-3 py-1.5 text-xs",
          "text-foreground hover:bg-muted",
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={t("modelHint")}
      >
        <span className="truncate">
          <span className="text-muted-foreground">{t("provider")}: </span>
          {activeProvider?.label ?? provider}
          <span className="mx-1 text-muted-foreground">·</span>
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
          <div className="absolute end-0 z-50 mt-1 flex max-h-80 w-[22rem] overflow-hidden rounded-lg border border-border bg-card shadow-xl">
            <ul
              role="listbox"
              aria-label={t("provider")}
              className="w-[40%] overflow-y-auto border-e border-border py-1"
            >
              {providers.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={row.id === provider}
                    onClick={() => {
                      const nextModel = row.models.includes(model) ? model : row.models[0];
                      setProviderModel(row.id, nextModel);
                    }}
                    className={cn(
                      "flex w-full px-3 py-2 text-start text-xs transition",
                      row.id === provider
                        ? "bg-primary/15 text-primary"
                        : "text-foreground hover:bg-muted",
                    )}
                  >
                    {row.label}
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex w-[60%] flex-col">
              <input
                value={modelQuery}
                onChange={(e) => setModelQuery(e.target.value)}
                placeholder={t("modelSearch")}
                className="border-b border-border bg-background px-3 py-2 text-xs outline-none"
                aria-label={t("modelSearch")}
              />
            <ul
              role="listbox"
              aria-label={t("model")}
              className="flex-1 overflow-y-auto py-1"
            >
              {models.map((item) => (
                <li key={item}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={item === model}
                    onClick={() => {
                      setProviderModel(provider, item);
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
              {!models.length ? (
                <li className="px-3 py-2 text-xs text-muted-foreground">{t("modelSearchEmpty")}</li>
              ) : null}
            </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
