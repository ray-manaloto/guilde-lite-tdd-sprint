import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.describe("Login Page", () => {
    test("should display login form", async ({ page }) => {
      await page.goto("/login");

      // Check for login form elements
      await expect(page.getByLabel(/^email$/i)).toBeVisible();
      await expect(page.getByLabel(/^password$/i)).toBeVisible();
      await expect(page.getByRole("button", { name: /^login$/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /continue with google/i })).toBeVisible();
    });

    test("should mark fields as required", async ({ page }) => {
      await page.goto("/login");

      await expect(page.getByLabel(/^email$/i)).toHaveJSProperty("required", true);
      await expect(page.getByLabel(/^password$/i)).toHaveJSProperty("required", true);
    });

    test("should show error for invalid credentials", async ({ page }) => {
      await page.goto("/login");

      // Fill in invalid credentials
      const emailInput = page.locator("input#email");
      const passwordInput = page.locator("input#password");

      await emailInput.fill("");
      await emailInput.click();
      await emailInput.type("invalid@example.com");
      await expect(emailInput).toHaveValue("invalid@example.com");
      await passwordInput.fill("wrongpassword");
      await expect(passwordInput).toHaveValue("wrongpassword");
      await page.getByRole("button", { name: /^login$/i }).click();

      // Should show error message
      await expect(page.getByText(/invalid email or password|login failed/i)).toBeVisible({
        timeout: 5000,
      });
    });

    test("should have link to registration", async ({ page }) => {
      await page.goto("/login");

      // Should have link to register page
      await expect(page.getByRole("link", { name: /^register$/i })).toBeVisible();
    });
  });

  test.describe("Registration Page", () => {
    test("should display registration form", async ({ page }) => {
      await page.goto("/register");

      // Check for registration form elements
      await expect(page.getByLabel(/name/i)).toBeVisible();
      await expect(page.getByLabel(/^email$/i)).toBeVisible();
      await expect(page.getByLabel(/^password$/i)).toBeVisible();
      await expect(page.getByLabel(/confirm password/i)).toBeVisible();
      await expect(page.getByRole("button", { name: /^register$/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /sign up with google/i })).toBeVisible();
    });

    test("should validate password confirmation", async ({ page }) => {
      await page.goto("/register");

      // Fill in mismatched passwords
      const emailInput = page.locator("input#email");
      const passwordInput = page.locator("input#password");
      const confirmInput = page.locator("input#confirmPassword");

      await emailInput.fill("");
      await emailInput.click();
      await emailInput.type("newuser@example.com");
      await expect(emailInput).toHaveValue("newuser@example.com");
      await passwordInput.fill("TestPassword123!");
      await expect(passwordInput).toHaveValue("TestPassword123!");
      await confirmInput.fill("DifferentPassword!");
      await expect(confirmInput).toHaveValue("DifferentPassword!");

      // Should show mismatch error
      await page.getByRole("button", { name: /^register$/i }).click();
      await expect(page.getByText(/passwords do not match/i)).toBeVisible();
    });

    test("should have link to login", async ({ page }) => {
      await page.goto("/register");

      // Should have link to login page
      await expect(page.getByRole("link", { name: /^login$/i })).toBeVisible();
    });
  });

  test.describe("Authenticated User", () => {
    // Use authenticated state from setup
    test.use({
      storageState: ".playwright/.auth/user.json",
    });

    test("should load dashboard for authenticated user", async ({ page }) => {
      await page.goto("/dashboard");
      await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
    });

    test("should show profile link and logout action", async ({ page }) => {
      await page.goto("/dashboard");

      // Should have user profile/menu element
      await expect(page.locator('a[href="/profile"]')).toBeVisible();
      await expect(page.getByRole("button", { name: /logout/i })).toBeVisible();
    });

    test("should be able to logout", async ({ page }) => {
      await page.goto("/dashboard");

      // Find and click logout button
      await page.getByRole("button", { name: /logout/i }).click();

      // Should be redirected to login
      await expect(page).toHaveURL(/login/i);
    });
  });
});
