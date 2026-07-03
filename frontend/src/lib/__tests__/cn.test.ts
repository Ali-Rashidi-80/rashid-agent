import { describe, expect, it } from "vitest";
import { cn } from "../cn";

describe("cn", () => {
  it("merges tailwind classes with last-wins", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });
});
