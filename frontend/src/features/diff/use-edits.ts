"use client";

import { useCallback, useState } from "react";
import type { FileEditPayload } from "@/lib/agent-store";

export interface PatchFileResult {
  path: string;
  ok: boolean;
  original_content?: string;
  modified_content?: string;
  preview_diff?: string;
  lint_error?: string | null;
}

export interface PatchResponse {
  ok: boolean;
  results: PatchFileResult[];
}

export function useEdits() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const preview = useCallback(async (files: FileEditPayload[]): Promise<PatchResponse | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/edits/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files }),
      });
      if (!response.ok) {
        throw new Error(`Preview failed (${response.status})`);
      }
      return (await response.json()) as PatchResponse;
    } catch (err) {
      setError((err as Error).message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const apply = useCallback(
    async (files: FileEditPayload[], previewConfirmed = false): Promise<PatchResponse | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/v1/edits/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            files,
            create_backup: true,
            preview_confirmed: previewConfirmed,
          }),
        });
        if (!response.ok) {
          throw new Error(`Apply failed (${response.status})`);
        }
        return (await response.json()) as PatchResponse;
      } catch (err) {
        setError((err as Error).message);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { preview, apply, isLoading, error };
}
