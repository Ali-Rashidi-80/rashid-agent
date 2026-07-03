import { create } from "zustand";

export type AgentMode = "ask" | "plan" | "agent";
export type StreamPhase = "idle" | "message" | "edits" | "done" | "error";

export interface LineEditPayload {
  start_number_line: number;
  end_number_line: number;
  code: string;
  new_code: string;
}

export interface FileEditPayload {
  path: string;
  edits: LineEditPayload[];
}

export interface AgentResult {
  message: string;
  pip: string;
  log: string;
  edits: FileEditPayload[];
}

interface AgentStore {
  mode: AgentMode;
  sessionId: string | null;
  phase: StreamPhase;
  setMode: (mode: AgentMode) => void;
  setSessionId: (sessionId: string | null) => void;
  setPhase: (phase: StreamPhase) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  mode: "ask",
  sessionId: null,
  phase: "idle",
  setMode: (mode) => set({ mode }),
  setSessionId: (sessionId) => set({ sessionId }),
  setPhase: (phase) => set({ phase }),
}));
