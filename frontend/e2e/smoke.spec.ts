import { test, expect } from "@playwright/test";

test.describe("Smoke", () => {
  test("home renders @smoke", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("login form renders @smoke", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel(/^email$/i)).toBeVisible();
    await expect(page.getByLabel(/^password$/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /^login$/i })).toBeVisible();
  });
});
