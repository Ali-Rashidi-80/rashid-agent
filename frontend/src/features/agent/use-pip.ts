"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { runPipCommand } from "@/lib/session-api";

export function usePipRunner() {
  const [pipLog, setPipLog] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const runPip = useCallback(async (command: string) => {
    const trimmed = command.trim();
    if (!trimmed) {
      return;
    }
    setIsRunning(true);
    try {
      const result = await runPipCommand(trimmed);
      const output = [result.stdout, result.stderr, result.error].filter(Boolean).join("\n");
      setPipLog(output || (result.ok ? "OK" : "Failed"));
      if (result.ok) {
        toast.success("pip completed");
      } else {
        toast.error("pip failed");
      }
    } catch (err) {
      const message = (err as Error).message;
      setPipLog(message);
      toast.error(message);
    } finally {
      setIsRunning(false);
    }
  }, []);

  return { pipLog, isRunning, runPip, clearPipLog: () => setPipLog(null) };
}
