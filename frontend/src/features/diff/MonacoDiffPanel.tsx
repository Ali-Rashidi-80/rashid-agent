"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { useResolvedThemeMode } from "@/lib/theme-engine";

const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  {
    ssr: false,
    loading: () => <MonacoLoading />,
  },
);

function MonacoLoading() {
  const t = useTranslations("diff");
  return (
    <div className="flex h-full min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      <Loader2 className="me-2 h-4 w-4 animate-spin" />
      {t("loading")}
    </div>
  );
}

interface MonacoDiffPanelProps {
  original: string;
  modified: string;
  language?: string;
  height?: string;
}

export function MonacoDiffPanel({
  original,
  modified,
  language = "typescript",
  height = "320px",
}: MonacoDiffPanelProps) {
  const t = useTranslations("diff");
  const resolvedMode = useResolvedThemeMode();

  if (!original && !modified) {
    return (
      <section className="glass-panel flex min-h-[240px] flex-1 items-center justify-center p-4 text-sm text-muted-foreground">
        {t("noDiff")}
      </section>
    );
  }

  return (
    <section className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="border-b border-border px-4 py-3 text-sm font-medium">
        {t("title")}
      </header>
      <div className="code-ltr min-h-0 flex-1">
        <DiffEditor
          height={height === "100%" ? "100%" : height}
          language={language}
          original={original}
          modified={modified}
          theme={resolvedMode === "dark" ? "vs-dark" : "light"}
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontFamily: "var(--font-mono), monospace",
          }}
        />
      </div>
    </section>
  );
}
