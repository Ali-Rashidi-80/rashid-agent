"use client";

import { create } from "zustand";

export const THEME_PRESETS = [
  "royal-violet",
  "midnight-gold",
  "ocean-sapphire",
  "rose-quartz",
  "emerald-forest",
  "graphite-pro",
  "desert-sand",
  "aurora-mesh",
] as const;

export type ThemePreset = (typeof THEME_PRESETS)[number];
export type ThemeMode = "light" | "dark" | "system";

export const DEFAULT_PRESET: ThemePreset = "royal-violet";
export const DEFAULT_MODE: ThemeMode = "dark";

const STORAGE_KEY = "rashid-theme";

interface StoredTheme {
  preset: ThemePreset;
  mode: ThemeMode;
}

interface ThemeStore extends StoredTheme {
  setPreset: (preset: ThemePreset) => void;
  setMode: (mode: ThemeMode) => void;
  hydrate: () => void;
}

function readStoredTheme(): StoredTheme {
  if (typeof window === "undefined") {
    return { preset: DEFAULT_PRESET, mode: DEFAULT_MODE };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { preset: DEFAULT_PRESET, mode: DEFAULT_MODE };
    }
    const parsed = JSON.parse(raw) as Partial<StoredTheme>;
    const preset = THEME_PRESETS.includes(parsed.preset as ThemePreset)
      ? (parsed.preset as ThemePreset)
      : DEFAULT_PRESET;
    const mode =
      parsed.mode === "light" || parsed.mode === "dark" || parsed.mode === "system"
        ? parsed.mode
        : DEFAULT_MODE;
    return { preset, mode };
  } catch {
    return { preset: DEFAULT_PRESET, mode: DEFAULT_MODE };
  }
}

function persistTheme(state: StoredTheme): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  ...readStoredTheme(),
  setPreset: (preset) => {
    const next = { preset, mode: get().mode };
    persistTheme(next);
    set({ preset });
  },
  setMode: (mode) => {
    const next = { preset: get().preset, mode };
    persistTheme(next);
    set({ mode });
  },
  hydrate: () => set(readStoredTheme()),
}));
