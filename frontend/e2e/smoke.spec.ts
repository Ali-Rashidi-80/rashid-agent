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

  test("new chat button and colored modes are present", async ({ page }) => {
    await page.goto("/fa");
    const newChat = page.getByRole("button", { name: /چت جدید/i });
    if (!(await newChat.isVisible().catch(() => false))) {
      await page.getByRole("button", { name: /نوار کناری|Toggle sidebar|sidebar/i }).first().click();
    }
    await expect(page.getByRole("button", { name: /چت جدید/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^پرسش$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^برنامه$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^ایجنت$/i })).toBeVisible();
  });
});
