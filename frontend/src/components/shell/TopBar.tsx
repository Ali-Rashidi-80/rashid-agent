"use client";

import { useTranslations } from "next-intl";
import { Menu, Palette, Sparkles } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { LocaleSwitcher } from "@/components/settings/LocaleSwitcher";
import { useAgentStore, type AgentMode } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface TopBarProps {
  onToggleSidebar: () => void;
}

const modes: { key: AgentMode; labelKey: "modeAsk" | "modePlan" | "modeAgent" }[] = [
  { key: "ask", labelKey: "modeAsk" },
  { key: "plan", labelKey: "modePlan" },
  { key: "agent", labelKey: "modeAgent" },
];

export function TopBar({ onToggleSidebar }: TopBarProps) {
  const t = useTranslations("topBar");
  const tCommon = useTranslations("common");
  const mode = useAgentStore((s) => s.mode);
  const setMode = useAgentStore((s) => s.setMode);

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-card backdrop-blur-md px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground lg:hidden"
        aria-label="Toggle sidebar"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-brand text-primary-foreground shadow-glow">
          <Sparkles className="h-4 w-4" />
        </div>
        <span className="hidden font-semibold sm:inline">{tCommon("appName")}</span>
      </div>

      <div className="ms-auto flex items-center gap-2">
        <div className="hidden items-center gap-1 rounded-lg border border-border p-1 md:flex">
          {modes.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setMode(item.key)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition",
                mode === item.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>

        <span className="hidden rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground lg:inline">
          {t("model")}: Metis
        </span>

        <LocaleSwitcher compact />

        <Link
          href="/settings"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground"
          aria-label={t("theme")}
        >
          <Palette className="h-4 w-4" />
        </Link>
      </div>
    </header>
  );
}
