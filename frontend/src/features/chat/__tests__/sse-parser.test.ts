import { describe, expect, it } from "vitest";
import { parseSSEBlock, reduceSSEContent } from "../sse-parser";

describe("parseSSEBlock", () => {
  it("parses message_delta events", () => {
    const parsed = parseSSEBlock('event: message_delta\ndata: {"delta":"hi"}');
    expect(parsed).toEqual({ event: "message_delta", data: { delta: "hi" } });
  });

  it("parses result events with message", () => {
    const parsed = parseSSEBlock(
      'event: result\ndata: {"message":"done","edits":[]}',
    );
    expect(parsed?.event).toBe("result");
    expect(parsed?.data.message).toBe("done");
  });

  it("parses multiline data fields", () => {
    const parsed = parseSSEBlock('event: message_delta\ndata: {"delta":"a"}\ndata: ');
    expect(parsed?.data.delta).toBe("a");
  });

  it("parses event id field", () => {
    const parsed = parseSSEBlock(
      'id: 1700000000000-0\nevent: message_delta\ndata: {"delta":"x"}',
    );
    expect(parsed?.id).toBe("1700000000000-0");
  });
});

describe("reduceSSEContent", () => {
  it("accumulates deltas", () => {
    const first = reduceSSEContent("", {
      event: "message_delta",
      data: { delta: "Hello" },
    });
    const second = reduceSSEContent(first.content, {
      event: "message_delta",
      data: { delta: " world" },
    });
    expect(second.content).toBe("Hello world");
  });

  it("replaces content on message_done", () => {
    const result = reduceSSEContent("partial", {
      event: "message_done",
      data: { message: "full text" },
    });
    expect(result.content).toBe("full text");
  });

  it("ignores heartbeat without changing content", () => {
    const result = reduceSSEContent("keep", {
      event: "heartbeat",
      data: { ts: 1 },
    });
    expect(result.content).toBe("keep");
    expect(result.error).toBeNull();
  });
});
