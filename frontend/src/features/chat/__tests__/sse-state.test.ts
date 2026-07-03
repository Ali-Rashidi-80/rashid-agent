import { describe, expect, it } from "vitest";
import { reduceSSEState, initialSSEState } from "../sse-state";

describe("reduceSSEState", () => {
  it("captures result edits from agent stream", () => {
    const state = reduceSSEState(initialSSEState, {
      event: "result",
      data: {
        message: "done",
        pip: "pip install x",
        log: "",
        edits: [{ path: "a.py", edits: [] }],
      },
    });
    expect(state.result?.edits).toHaveLength(1);
    expect(state.result?.pip).toBe("pip install x");
    expect(state.phase).toBe("done");
  });

  it("tracks edits_generating phase", () => {
    const state = reduceSSEState(initialSSEState, {
      event: "edits_generating",
      data: {},
    });
    expect(state.phase).toBe("edits");
  });

  it("marks cancelled done as error phase", () => {
    const state = reduceSSEState(initialSSEState, {
      event: "done",
      data: { request_id: "abc", cancelled: true },
    });
    expect(state.phase).toBe("error");
  });

  it("records reconnect_degraded warning", () => {
    const state = reduceSSEState(initialSSEState, {
      event: "reconnect_degraded",
      data: { message: "Redis replay unavailable" },
    });
    expect(state.warnings).toContain("Redis replay unavailable");
  });

  it("records verify issues as warnings", () => {
    const state = reduceSSEState(initialSSEState, {
      event: "verify",
      data: { ok: false, issues: ["bad.py: syntax error"] },
    });
    expect(state.warnings).toContain("bad.py: syntax error");
  });
});
