import { describe, expect, it } from "vitest";
import { isStreamIncomplete } from "../use-sse";
import { initialSSEState } from "../sse-state";

describe("isStreamIncomplete", () => {
  it("returns true when stream has no terminal state", () => {
    expect(isStreamIncomplete({ ...initialSSEState, phase: "message", content: "hi" })).toBe(
      true,
    );
  });

  it("returns false when result is present", () => {
    expect(
      isStreamIncomplete({
        ...initialSSEState,
        phase: "message",
        result: { message: "ok", pip: "", log: "", edits: [] },
      }),
    ).toBe(false);
  });

  it("returns false on error phase", () => {
    expect(
      isStreamIncomplete({ ...initialSSEState, phase: "error", error: "failed" }),
    ).toBe(false);
  });
});

describe("reconnect backoff", () => {
  it("defines three retry delays and four attempts", async () => {
    const { RECONNECT_DELAYS_MS, RECONNECT_ATTEMPTS } = await import("../use-sse");
    expect(RECONNECT_DELAYS_MS).toEqual([1000, 2000, 4000]);
    expect(RECONNECT_ATTEMPTS).toBe(4);
  });
});
