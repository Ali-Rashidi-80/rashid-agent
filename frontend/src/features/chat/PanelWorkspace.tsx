"use client";

import { useCallback, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { Columns2, Maximize2, PanelLeft, PanelRight } from "lucide-react";
import { useAgentStore } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface PanelWorkspaceProps {
  output: React.ReactNode;
  diff: React.ReactNode;
}

export function PanelWorkspace({ output, diff }: PanelWorkspaceProps) {
  const t = useTranslations("layout");
  const panelFocus = useAgentStore((s) => s.panelFocus);
  const splitRatio = useAgentStore((s) => s.splitRatio);
  const setPanelFocus = useAgentStore((s) => s.setPanelFocus);
  const setSplitRatio = useAgentStore((s) => s.setSplitRatio);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onPointerMove = useCallback(
    (event: PointerEvent) => {
      if (!dragging.current || !containerRef.current) {
        return;
      }
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width <= 0) {
        return;
      }
      setSplitRatio((event.clientX - rect.left) / rect.width);
    },
    [setSplitRatio],
  );

  const stopDrag = useCallback(() => {
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDrag);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDrag);
    };
  }, [onPointerMove, stopDrag]);

  const showOutput = panelFocus !== "diff";
  const showDiff = panelFocus !== "output";

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1 px-1">
        <button
          type="button"
          title={`${t("focusOutput")} (Ctrl+Alt+1)`}
          onClick={() => setPanelFocus("output")}
          className={cn(
            "inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px]",
            panelFocus === "output" ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
        >
          <PanelLeft className="h-3.5 w-3.5" />
          {t("output")}
        </button>
        <button
          type="button"
          title={`${t("focusDiff")} (Ctrl+Alt+2)`}
          onClick={() => setPanelFocus("diff")}
          className={cn(
            "inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px]",
            panelFocus === "diff" ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
        >
          <PanelRight className="h-3.5 w-3.5" />
          {t("diff")}
        </button>
        <button
          type="button"
          title={`${t("splitView")} (Ctrl+Alt+0)`}
          onClick={() => setPanelFocus("split")}
          className={cn(
            "inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px]",
            panelFocus === "split" ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
        >
          <Columns2 className="h-3.5 w-3.5" />
          {t("split")}
        </button>
        <span className="ms-auto hidden items-center gap-1 text-[10px] text-muted-foreground sm:inline-flex">
          <Maximize2 className="h-3 w-3" />
          {t("dragHint")}
        </span>
      </div>

      <div
        ref={containerRef}
        className="grid min-h-0 flex-1 gap-0"
        style={
          panelFocus === "split"
            ? {
                gridTemplateColumns: `${Math.round(splitRatio * 100)}% 8px 1fr`,
              }
            : { gridTemplateColumns: "1fr" }
        }
      >
        {showOutput && <div className="flex min-h-0 min-w-0 flex-col">{output}</div>}

        {panelFocus === "split" && (
          <button
            type="button"
            aria-label={t("resize")}
            title={t("resize")}
            onPointerDown={(event) => {
              event.preventDefault();
              dragging.current = true;
              document.body.style.cursor = "col-resize";
              document.body.style.userSelect = "none";
            }}
            className="hidden cursor-col-resize rounded-sm bg-border/60 transition hover:bg-primary/50 lg:block"
          />
        )}

        {showDiff && <div className="flex min-h-0 min-w-0 flex-col">{diff}</div>}
      </div>
    </div>
  );
}
