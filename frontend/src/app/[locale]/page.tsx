"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PromptComposer } from "@/features/chat/PromptComposer";
import { OutputPanel } from "@/features/chat/OutputPanel";
import { useSSE } from "@/features/chat/use-sse";
import { DiffActions } from "@/features/diff/DiffActions";
import { MonacoDiffPanel } from "@/features/diff/MonacoDiffPanel";
import { usePipRunner } from "@/features/agent/use-pip";
import { useEdits } from "@/features/diff/use-edits";

function guessLanguage(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "typescript";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "javascript";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".md")) return "markdown";
  return "plaintext";
}

export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const { content, isStreaming, error, phase, result, start, stop } = useSSE();
  const { preview, apply, isLoading, error: editsError } = useEdits();
  const { pipLog, runPip, isRunning: pipRunning } = usePipRunner();
  const [original, setOriginal] = useState("");
  const [modified, setModified] = useState("");
  const [diffLanguage, setDiffLanguage] = useState("typescript");
  const [previewReady, setPreviewReady] = useState(false);
  const previewConfirmedRef = useRef(false);
  const previewEpochRef = useRef(0);

  const loadDiffFromPreview = useCallback(async (): Promise<boolean> => {
    const epoch = previewEpochRef.current;
    if (!result?.edits?.length) {
      return false;
    }
    const response = await preview(result.edits);
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
  }, [preview, result]);

  useEffect(() => {
    previewEpochRef.current += 1;
    previewConfirmedRef.current = false;
    setPreviewReady(false);
    if (result?.edits?.length && !isStreaming) {
      void loadDiffFromPreview();
    } else if (!result?.edits?.length) {
      setOriginal("");
      setModified("");
    }
  }, [result, isStreaming, loadDiffFromPreview]);

  const handleSubmit = () => {
    if (!prompt.trim() || isStreaming) {
      return;
    }
    start({ prompt });
  };

  const handleApply = async (): Promise<boolean> => {
    if (!result?.edits?.length) {
      return false;
    }
    const response = await apply(result.edits, previewConfirmedRef.current);
    if (!response?.ok) {
      return false;
    }
    return loadDiffFromPreview();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <PromptComposer
        value={prompt}
        onChange={setPrompt}
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
      />

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
        <OutputPanel
          content={content}
          isStreaming={isStreaming}
          error={error}
          phase={phase}
          agentLog={result?.log || pipLog || undefined}
          pipCommand={result?.pip?.trim() || undefined}
          onRunPip={runPip}
          pipRunning={pipRunning}
        />
        <div className="flex min-h-0 flex-col">
          <MonacoDiffPanel
            original={original}
            modified={modified}
            language={diffLanguage}
            height="320px"
          />
          {editsError && (
            <p className="border-t border-border px-4 py-2 text-xs text-red-400">{editsError}</p>
          )}
          <DiffActions
            hasEdits={Boolean(result?.edits?.length)}
            isLoading={isLoading}
            canApply={previewReady}
            onPreview={loadDiffFromPreview}
            onApply={handleApply}
          />
        </div>
      </div>
    </div>
  );
}
