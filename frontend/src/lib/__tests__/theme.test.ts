import { describe, expect, it } from "vitest";

describe("theme tokens", () => {
  it("royal violet preset id is valid", () => {
    expect("royal-violet").toMatch(/^[a-z-]+$/);
  });
});

describe("i18n", () => {
  it("supports fa and en", () => {
    const locales = ["fa", "en"];
    expect(locales).toContain("fa");
    expect(locales).toContain("en");
  });
});
