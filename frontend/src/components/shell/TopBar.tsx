"use client";

import { useTranslations } from "next-intl";
import { Menu, Palette, Sparkles } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { LocaleSwitcher } from "@/components/settings/LocaleSwitcher";
import { ModelSelector } from "@/components/shell/ModelSelector";
import { MODE_STYLES, useAgentStore, type AgentMode } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface TopBarProps {
  onToggleSidebar: () => void;
}

const modes: {
  key: AgentMode;
  labelKey: "modeAsk" | "modePlan" | "modeAgent";
  hintKey: "modeAskHint" | "modePlanHint" | "modeAgentHint";
}[] = [
  { key: "ask", labelKey: "modeAsk", hintKey: "modeAskHint" },
  { key: "plan", labelKey: "modePlan", hintKey: "modePlanHint" },
  { key: "agent", labelKey: "modeAgent", hintKey: "modeAgentHint" },
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
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground"
        aria-label={t("toggleSidebar")}
        title={`${t("toggleSidebar")} (Ctrl+B)`}
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
        <div
          className="flex items-center gap-1 rounded-lg border border-border p-1"
          title={t("cycleModesHint")}
        >
          {modes.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setMode(item.key)}
              title={t(item.hintKey)}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-medium transition sm:px-3",
                mode === item.key ? MODE_STYLES[item.key].active : MODE_STYLES[item.key].idle,
              )}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>

        <ModelSelector />

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
