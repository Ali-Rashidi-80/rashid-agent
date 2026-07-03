import { describe, expect, it } from "vitest";
import { THEME_PRESETS, DEFAULT_PRESET } from "@/lib/theme-store";

describe("design system", () => {
  it.each(THEME_PRESETS)("preset %s is kebab-case", (id) => {
    expect(id).toMatch(/^[a-z0-9-]+$/);
  });

  it("has 8 presets", () => {
    expect(THEME_PRESETS).toHaveLength(8);
  });

  it("default is royal-violet", () => {
    expect(DEFAULT_PRESET).toBe("royal-violet");
  });
});

describe("storage keys", () => {
  it("uses rashid namespace", () => {
    expect("rashid-theme").toMatch(/^rashid-/);
  });
});
