import { expect, test } from "@playwright/test";

test.describe("Rashid UI smoke", () => {
  test("Persian home loads composer", async ({ page }) => {
    await page.goto("/fa");
    await expect(page.getByRole("heading", { name: /خروجی/i })).toBeVisible();
    await expect(page.getByPlaceholder(/توضیح دهید/i)).toBeVisible();
  });

  test("English home loads composer", async ({ page }) => {
    await page.goto("/en");
    await expect(page.getByRole("heading", { name: /Output/i })).toBeVisible();
    await expect(page.getByPlaceholder(/Describe what you want/i)).toBeVisible();
  });

  test("settings page loads", async ({ page }) => {
    await page.goto("/fa/settings");
    await expect(page.getByRole("heading", { name: /تنظیمات/i })).toBeVisible();
  });

  test("RTL layout on Persian locale", async ({ page }) => {
    await page.goto("/fa");
    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("rtl");
  });
});
