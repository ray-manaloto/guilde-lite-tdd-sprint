import { test, expect } from '@playwright/test';

test('Recursive Agent Browser Flow', async ({ page }) => {
    // --- Authentication Step ---
    const testEmail = `recursive-agent-${Date.now()}@example.com`;
    const testPassword = "TestPassword123!";

    // 1. Register User (API) to ensure account exists
    // Hit Backend directly to bypass potential Next.js proxy issues/500s during test setup
    const regResponse = await page.request.post("http://localhost:8000/api/v1/auth/register", {
        data: {
            email: testEmail,
            password: testPassword,
            full_name: "Recursive Agent Test User",
        },
    });
    if (regResponse.status() !== 200 && regResponse.status() !== 400) {
        console.log("Registration Failed:", regResponse.status());
        console.log("Response Body:", await regResponse.text());
    }
    expect(regResponse.status() === 200 || regResponse.status() === 201 || regResponse.status() === 400).toBeTruthy();

    // 2. Login (UI)
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(testEmail);
    await page.getByLabel(/password/i).fill(testPassword);

    // Click submit and wait for navigation
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();

    // 3. Wait for Dashboard/Chat redirection
    await expect(page).toHaveURL(/dashboard/i, { timeout: 15000 });

    // --- Chat Flow ---

    // 4. Navigate to Chat explicitly
    await page.goto('/chat');

    // 5. Wait for chat input
    const input = page.getByPlaceholder("Type a message...");
    await expect(input).toBeVisible();

    // 6. Type request
    await input.fill('Go to https://www.google.com and tell me the title of the page.');

    // 7. Send message
    await page.keyboard.press('Enter');

    // 8. Wait for response
    // The agent takes time to "think" and run the tool
    const responseLocator = page.locator('.prose-sm').filter({ hasText: /Google/i });

    // Increase timeout to 45s for full round trip and tool execution delay
    // We expect the word "Google" in the response (e.g. "The title is Google")
    await expect(responseLocator).toBeVisible({ timeout: 45000 });
});
