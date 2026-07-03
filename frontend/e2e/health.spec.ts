import { expect, test } from "@playwright/test";

test.describe("API proxy smoke", () => {
  test("status bar shows connected when health mock succeeds", async ({ page }) => {
    await page.route("**/api/v1/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          postgres: { status: "ok" },
          redis: { status: "ok" },
          worker: { status: "ok" },
        }),
      });
    });

    await page.route("**/api/v1/project/path", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "project_path not set" }),
      });
    });

    await page.goto("/fa");
    await expect(page.getByText("متصل")).toBeVisible();
  });

  test("status bar shows disconnected when health fails", async ({ page }) => {
    await page.route("**/api/v1/health", async (route) => {
      await route.fulfill({ status: 503, body: "unavailable" });
    });

    await page.goto("/en");
    await expect(page.getByText("Disconnected")).toBeVisible();
  });
});
