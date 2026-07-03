"use client";

import { useTranslations } from "next-intl";
import {
  THEME_PRESETS,
  type ThemeMode,
  type ThemePreset,
  useThemeStore,
} from "@/lib/theme-store";
import { cn } from "@/lib/cn";

const PRESET_SWATCHES: Record<ThemePreset, string> = {
  "royal-violet": "from-violet-500 to-indigo-600",
  "midnight-gold": "from-zinc-700 to-amber-500",
  "ocean-sapphire": "from-sky-600 to-blue-800",
  "rose-quartz": "from-rose-400 to-pink-300",
  "emerald-forest": "from-emerald-600 to-green-800",
  "graphite-pro": "from-zinc-400 to-zinc-700",
  "desert-sand": "from-amber-300 to-orange-400",
  "aurora-mesh": "from-fuchsia-500 via-cyan-400 to-violet-500",
};

const MODES: ThemeMode[] = ["light", "dark", "system"];

const MODE_LABELS: Record<ThemeMode, "modeLight" | "modeDark" | "modeSystem"> = {
  light: "modeLight",
  dark: "modeDark",
  system: "modeSystem",
};

export function ThemePicker() {
  const t = useTranslations("settings");
  const tThemes = useTranslations("themes");
  const preset = useThemeStore((s) => s.preset);
  const mode = useThemeStore((s) => s.mode);
  const setPreset = useThemeStore((s) => s.setPreset);
  const setMode = useThemeStore((s) => s.setMode);

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-3 text-sm font-medium">{t("themePreset")}</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {THEME_PRESETS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setPreset(item)}
              className={cn(
                "rounded-xl border p-3 text-start transition",
                preset === item
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary/40",
              )}
            >
              <div
                className={cn(
                  "mb-2 h-10 rounded-lg bg-gradient-to-br",
                  PRESET_SWATCHES[item],
                )}
              />
              <span className="text-xs font-medium">{tThemes(item)}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-3 text-sm font-medium">{t("themeMode")}</p>
        <div className="inline-flex rounded-lg border border-border p-1">
          {MODES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setMode(item)}
              className={cn(
                "rounded-md px-4 py-2 text-sm transition",
                mode === item
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {t(MODE_LABELS[item])}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
