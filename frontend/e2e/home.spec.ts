import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("should load the home page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/guilde_lite_tdd_sprint/i);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/guilde_lite_tdd_sprint/i);
  });

  test("should show key feature cards", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Authentication", { exact: true })).toBeVisible();
    await expect(page.getByText("AI Assistant", { exact: true })).toBeVisible();
    await expect(page.getByText("Dashboard", { exact: true })).toBeVisible();
  });

  test("should expose auth actions", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: /^login$/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /^register$/i })).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("should navigate between pages", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: /^login$/i }).click();
    await expect(page).toHaveURL(/\/login/i);

    await page.goto("/");
    await page.getByRole("link", { name: /^register$/i }).click();
    await expect(page).toHaveURL(/\/register/i);
  });
});

test.describe("Responsive Design", () => {
  test("should work on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Page should still be functional
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("should work on tablet viewport", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/");

    // Page should still be functional
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });
});
