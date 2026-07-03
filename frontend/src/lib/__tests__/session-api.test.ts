import { afterEach, describe, expect, it, vi } from "vitest";
import { ensureChatSession } from "../session-api";

describe("ensureChatSession", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("reuses session when project path matches", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/sessions/existing-id")) {
          return new Response(
            JSON.stringify({
              id: "existing-id",
              project_path: "/proj/a",
              title: "Chat",
              mode: "ask",
            }),
            { status: 200 },
          );
        }
        throw new Error(`unexpected fetch: ${url}`);
      }),
    );

    const id = await ensureChatSession("/proj/a", "ask", "existing-id");
    expect(id).toBe("existing-id");
  });

  it("creates new session when project path mismatches", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/sessions/old-id")) {
          return new Response(
            JSON.stringify({
              id: "old-id",
              project_path: "/proj/old",
              title: "Chat",
              mode: "ask",
            }),
            { status: 200 },
          );
        }
        if (url.endsWith("/sessions") && init?.method === "POST") {
          return new Response(JSON.stringify({ id: "new-id" }), { status: 200 });
        }
        throw new Error(`unexpected fetch: ${url}`);
      }),
    );

    const id = await ensureChatSession("/proj/new", "ask", "old-id");
    expect(id).toBe("new-id");
  });
});
