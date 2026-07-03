import { describe, expect, it } from "vitest";
import { THEME_PRESETS } from "../theme-store";

describe("theme-store", () => {
  it("defines eight presets matching CSS theme files", () => {
    expect(THEME_PRESETS).toHaveLength(8);
    expect(THEME_PRESETS).toContain("royal-violet");
    expect(THEME_PRESETS).toContain("aurora-mesh");
  });
});
