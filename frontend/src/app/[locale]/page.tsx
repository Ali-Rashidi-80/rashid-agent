"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { PromptComposer } from "@/features/chat/PromptComposer";
import { OutputPanel } from "@/features/chat/OutputPanel";
import { PanelWorkspace } from "@/features/chat/PanelWorkspace";
import { useSSE } from "@/features/chat/use-sse";
import { DiffActions } from "@/features/diff/DiffActions";
import { MonacoDiffPanel } from "@/features/diff/MonacoDiffPanel";
import { usePipRunner } from "@/features/agent/use-pip";
import { useEdits } from "@/features/diff/use-edits";
import { useAgentStore } from "@/lib/agent-store";

function guessLanguage(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "typescript";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "javascript";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".md")) return "markdown";
  return "plaintext";
}

export default function HomePage() {
  const t = useTranslations("chat");
  const [prompt, setPrompt] = useState("");
  const { content, isStreaming, error, phase, result, sources, start, stop, reset } = useSSE();
  const { preview, apply, isLoading, error: editsError } = useEdits();
  const { pipLog, runPip, isRunning: pipRunning } = usePipRunner();
  const [original, setOriginal] = useState("");
  const [modified, setModified] = useState("");
  const [diffLanguage, setDiffLanguage] = useState("typescript");
  const [previewReady, setPreviewReady] = useState(false);
  const previewConfirmedRef = useRef(false);
  const previewEpochRef = useRef(0);

  const mode = useAgentStore((s) => s.mode);
  const chatEpoch = useAgentStore((s) => s.chatEpoch);
  const restoredResult = useAgentStore((s) => s.restoredResult);
  const setRestoredResult = useAgentStore((s) => s.setRestoredResult);

  const activeResult = result ?? restoredResult;
  const editsEnabled = mode === "agent";

  useEffect(() => {
    reset();
    setPrompt("");
    setOriginal("");
    setModified("");
    previewConfirmedRef.current = false;
    setPreviewReady(false);
  }, [chatEpoch, reset]);

  const loadDiffFromPreview = useCallback(async (): Promise<boolean> => {
    const epoch = previewEpochRef.current;
    if (!activeResult?.edits?.length) {
      return false;
    }
    const response = await preview(activeResult.edits);
    if (epoch !== previewEpochRef.current) {
      return false;
    }
    if (!response?.ok) {
      previewConfirmedRef.current = false;
      setPreviewReady(false);
      return false;
    }
    const first = response.results?.find((item) => item.ok);
    if (!first || epoch !== previewEpochRef.current) {
      previewConfirmedRef.current = false;
      setPreviewReady(false);
      return false;
    }
    setOriginal(first.original_content ?? "");
    setModified(first.modified_content ?? "");
    setDiffLanguage(guessLanguage(first.path));
    previewConfirmedRef.current = true;
    setPreviewReady(true);
    return true;
  }, [preview, activeResult]);

  useEffect(() => {
    previewEpochRef.current += 1;
    previewConfirmedRef.current = false;
    setPreviewReady(false);
    if (activeResult?.edits?.length && !isStreaming && editsEnabled) {
      void loadDiffFromPreview();
    } else if (!activeResult?.edits?.length) {
      setOriginal("");
      setModified("");
    }
  }, [activeResult, isStreaming, loadDiffFromPreview, editsEnabled]);

  useEffect(() => {
    if (result) {
      setRestoredResult(null);
    }
  }, [result, setRestoredResult]);

  const handleSubmit = () => {
    if (!prompt.trim() || isStreaming) {
      return;
    }
    start({ prompt });
    setPrompt("");
  };

  const handleApply = async (): Promise<boolean> => {
    if (!activeResult?.edits?.length || !editsEnabled) {
      return false;
    }
    const response = await apply(activeResult.edits, previewConfirmedRef.current);
    if (!response?.ok) {
      return false;
    }
    return loadDiffFromPreview();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <PromptComposer
        value={prompt}
        onChange={setPrompt}
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
      />

      {mode !== "agent" && (
        <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          {mode === "ask" ? t("askModeHint") : t("planModeHint")}
        </p>
      )}

      <PanelWorkspace
        output={
          <OutputPanel
            content={content}
            isStreaming={isStreaming}
            error={error}
            phase={phase}
            agentLog={activeResult?.log || pipLog || undefined}
            pipCommand={activeResult?.pip?.trim() || undefined}
            onRunPip={runPip}
            pipRunning={pipRunning}
            sources={sources}
          />
        }
        diff={
          <div className="flex min-h-0 flex-1 flex-col">
            <MonacoDiffPanel
              original={original}
              modified={modified}
              language={diffLanguage}
              height="100%"
            />
            {editsError && (
              <p className="border-t border-border px-4 py-2 text-xs text-red-400">{editsError}</p>
            )}
            {editsEnabled ? (
              <DiffActions
                hasEdits={Boolean(activeResult?.edits?.length)}
                isLoading={isLoading}
                canApply={previewReady}
                onPreview={loadDiffFromPreview}
                onApply={handleApply}
              />
            ) : (
              <p className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
                {t("diffDisabledHint")}
              </p>
            )}
          </div>
        }
      />
    </div>
  );
}
