"use client";

import { useEffect, useState } from "react";
import { useThemeStore, type ThemeMode } from "./theme-store";

function resolveMode(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") {
    if (typeof window === "undefined") {
      return "dark";
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return mode;
}

function applyTheme(preset: string, mode: ThemeMode): void {
  const root = document.documentElement;
  root.setAttribute("data-preset", preset);
  const resolved = resolveMode(mode);
  root.classList.toggle("dark", resolved === "dark");
  root.classList.toggle("light", resolved === "light");
}

export function ThemeEngine() {
  const preset = useThemeStore((s) => s.preset);
  const mode = useThemeStore((s) => s.mode);
  const hydrate = useThemeStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    applyTheme(preset, mode);
  }, [preset, mode]);

  useEffect(() => {
    if (mode !== "system") {
      return;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme(preset, "system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [mode, preset]);

  return null;
}

export function useResolvedThemeMode(): "light" | "dark" {
  const mode = useThemeStore((s) => s.mode);
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolveMode(mode));

  useEffect(() => {
    setResolved(resolveMode(mode));
    if (mode !== "system") {
      return;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolved(media.matches ? "dark" : "light");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [mode]);

  return resolved;
}
