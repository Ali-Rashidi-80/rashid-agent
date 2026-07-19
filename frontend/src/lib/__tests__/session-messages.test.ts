import { describe, expect, it } from "vitest";
import {
  extractAssistantResult,
  extractAssistantText,
  titleFromPrompt,
} from "../session-api";

describe("session message helpers", () => {
  it("extracts message from stored assistant JSON", () => {
    const raw = JSON.stringify({
      message: "سلام رشید",
      pip: "",
      edits: [],
      log: "",
    });
    expect(extractAssistantText(raw)).toBe("سلام رشید");
    expect(extractAssistantResult(raw)?.message).toBe("سلام رشید");
  });

  it("falls back to plain text", () => {
    expect(extractAssistantText("plain answer")).toBe("plain answer");
    expect(extractAssistantResult("plain answer")).toBeNull();
  });

  it("builds title from prompt", () => {
    expect(titleFromPrompt("hello world", "ask")).toBe("hello world");
    expect(titleFromPrompt("a".repeat(60), "agent").endsWith("…")).toBe(true);
    expect(titleFromPrompt("   ", "plan")).toBe("plan");
  });
});
