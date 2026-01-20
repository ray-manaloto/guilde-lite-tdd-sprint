import { test as setup, expect } from "@playwright/test";
import path from "path";

const authFile = path.join(__dirname, "../.playwright/.auth/user.json");

/**
 * Authentication setup - runs before all tests.
 *
 * This creates an authenticated session that other tests can reuse.
 */
setup("authenticate", async ({ page }) => {
  // Test credentials - adjust for your environment
  const testEmail =
    process.env.TEST_USER_EMAIL || `test+${Date.now()}@example.com`;
  const testPassword = process.env.TEST_USER_PASSWORD || "TestPassword123!";

  // Ensure user exists (ignore if already registered)
  const registerResponse = await page.request.post("/api/auth/register", {
    data: {
      email: testEmail,
      password: testPassword,
      full_name: "Playwright Test User",
    },
  });

  if (!registerResponse.ok() && registerResponse.status() !== 400) {
    throw new Error(
      `Failed to register test user (status ${registerResponse.status()})`
    );
  }

  // Navigate to login page
  await page.goto("/login");

  // Fill in login form
  await page.getByLabel(/email/i).fill(testEmail);
  await page.getByLabel(/password/i).fill(testPassword);

  // Submit and wait for redirect
  await page.getByRole("button", { name: /sign in|log in|login/i }).click();

  // Wait for authentication to complete
  await expect(page).toHaveURL(/dashboard/i, { timeout: 10000 });

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
