import { create } from "zustand";

export type AgentMode = "ask" | "plan" | "agent";
export type StreamPhase = "idle" | "message" | "edits" | "done" | "error";
export type PanelFocus = "split" | "output" | "diff";

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

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface AgentStore {
  mode: AgentMode;
  model: string;
  sessionId: string | null;
  phase: StreamPhase;
  transcript: ChatTurn[];
  restoredResult: AgentResult | null;
  chatEpoch: number;
  sidebarOpen: boolean;
  panelFocus: PanelFocus;
  splitRatio: number;
  hydrated: boolean;
  setMode: (mode: AgentMode) => void;
  cycleMode: () => void;
  setModel: (model: string) => void;
  setSessionId: (sessionId: string | null) => void;
  setPhase: (phase: StreamPhase) => void;
  setTranscript: (turns: ChatTurn[]) => void;
  appendTurn: (turn: ChatTurn) => void;
  clearTranscript: () => void;
  setRestoredResult: (result: AgentResult | null) => void;
  bumpChatEpoch: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setPanelFocus: (focus: PanelFocus) => void;
  setSplitRatio: (ratio: number) => void;
  startNewChat: () => void;
  hydrate: () => void;
}

const MODE_ORDER: AgentMode[] = ["ask", "plan", "agent"];
const DEFAULT_MODEL = "grok-code-fast-1";
const STORAGE_KEY = "rashid-agent-ui";

interface PersistedUi {
  mode?: AgentMode;
  model?: string;
  sidebarOpen?: boolean;
  splitRatio?: number;
  panelFocus?: PanelFocus;
}

function readPersisted(): PersistedUi {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    return JSON.parse(raw) as PersistedUi;
  } catch {
    return {};
  }
}

function writePersisted(partial: PersistedUi) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const current = readPersisted();
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...partial }));
  } catch {
    // ignore quota / private mode
  }
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  mode: "ask",
  model: DEFAULT_MODEL,
  sessionId: null,
  phase: "idle",
  transcript: [],
  restoredResult: null,
  chatEpoch: 0,
  sidebarOpen: true,
  panelFocus: "split",
  splitRatio: 0.55,
  hydrated: false,
  setMode: (mode) => {
    writePersisted({ mode });
    set({ mode });
  },
  cycleMode: () => {
    const current = get().mode;
    const next = MODE_ORDER[(MODE_ORDER.indexOf(current) + 1) % MODE_ORDER.length];
    writePersisted({ mode: next });
    set({ mode: next });
  },
  setModel: (model) => {
    writePersisted({ model });
    set({ model });
  },
  setSessionId: (sessionId) => set({ sessionId }),
  setPhase: (phase) => set({ phase }),
  setTranscript: (turns) => set({ transcript: turns }),
  appendTurn: (turn) => set((state) => ({ transcript: [...state.transcript, turn] })),
  clearTranscript: () => set({ transcript: [] }),
  setRestoredResult: (result) => set({ restoredResult: result }),
  bumpChatEpoch: () => set((state) => ({ chatEpoch: state.chatEpoch + 1 })),
  setSidebarOpen: (open) => {
    writePersisted({ sidebarOpen: open });
    set({ sidebarOpen: open });
  },
  toggleSidebar: () => {
    const open = !get().sidebarOpen;
    writePersisted({ sidebarOpen: open });
    set({ sidebarOpen: open });
  },
  setPanelFocus: (focus) => {
    writePersisted({ panelFocus: focus });
    set({ panelFocus: focus });
  },
  setSplitRatio: (ratio) => {
    const next = Math.min(0.8, Math.max(0.2, ratio));
    writePersisted({ splitRatio: next, panelFocus: "split" });
    set({ splitRatio: next, panelFocus: "split" });
  },
  startNewChat: () =>
    set((state) => ({
      sessionId: null,
      transcript: [],
      restoredResult: null,
      phase: "idle",
      chatEpoch: state.chatEpoch + 1,
    })),
  hydrate: () => {
    if (get().hydrated) {
      return;
    }
    const stored = readPersisted();
    set({
      hydrated: true,
      mode: stored.mode === "ask" || stored.mode === "plan" || stored.mode === "agent" ? stored.mode : "ask",
      model: typeof stored.model === "string" && stored.model ? stored.model : DEFAULT_MODEL,
      sidebarOpen: stored.sidebarOpen ?? true,
      splitRatio:
        typeof stored.splitRatio === "number" ? Math.min(0.8, Math.max(0.2, stored.splitRatio)) : 0.55,
      panelFocus:
        stored.panelFocus === "output" || stored.panelFocus === "diff" || stored.panelFocus === "split"
          ? stored.panelFocus
          : "split",
    });
  },
}));

export const MODE_STYLES: Record<
  AgentMode,
  { active: string; idle: string; ring: string; label: string }
> = {
  ask: {
    active: "bg-sky-600 text-white shadow-sm shadow-sky-900/40",
    idle: "text-sky-700 hover:bg-sky-500/15 hover:text-sky-900 dark:text-sky-300/80 dark:hover:text-sky-100",
    ring: "ring-sky-500/40",
    label: "text-sky-700 dark:text-sky-300",
  },
  plan: {
    active: "bg-amber-600 text-white shadow-sm shadow-amber-900/40",
    idle: "text-amber-700 hover:bg-amber-500/15 hover:text-amber-900 dark:text-amber-300/80 dark:hover:text-amber-100",
    ring: "ring-amber-500/40",
    label: "text-amber-700 dark:text-amber-300",
  },
  agent: {
    active: "bg-emerald-600 text-white shadow-sm shadow-emerald-900/40",
    idle: "text-emerald-700 hover:bg-emerald-500/15 hover:text-emerald-900 dark:text-emerald-300/80 dark:hover:text-emerald-100",
    ring: "ring-emerald-500/40",
    label: "text-emerald-700 dark:text-emerald-300",
  },
};
