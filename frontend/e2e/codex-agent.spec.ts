
import { test, expect } from '@playwright/test';

test('Codex Agent Integration Flow', async ({ page }) => {
    test.setTimeout(120000); // Allow 2 minutes for agent interactions

    // --- Authentication ---
    const testEmail = `codex-agent-${Date.now()}@example.com`;
    const testPassword = "TestPassword123!";

    // Register User directly via Backend API
    const regResponse = await page.request.post(`${process.env.BACKEND_URL || 'http://localhost:8000'}/api/v1/auth/register`, {
        data: {
            email: testEmail,
            password: testPassword,
            full_name: "Codex Agent Test User",
        },
    });

    if (regResponse.status() !== 200 && regResponse.status() !== 201 && regResponse.status() !== 400) {
        console.log("Registration Failed:", regResponse.status());
    }

    // Login
    await page.goto('/login');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();

    // Wait for Dashboard/Chat
    await expect(page).toHaveURL(/dashboard/i, { timeout: 15000 });

    // --- Chat Flow ---
    await page.goto('/chat');

    // Wait for chat input
    const input = page.getByPlaceholder("Type a message...");
    await expect(input).toBeVisible();

    // Test Codex Tool
    const codexPayload = `unique_codex_val_${Date.now()}`;
    // We explicitly ask the agent to use the 'call_codex_agent' tool.
    // The prompt mimics a simple CLI execution request.
    await input.fill(`Please verify the Codex tool is working. Use the 'call_codex_agent' tool to execute 'echo ${codexPayload}'. Return the output exactly.`);
    await page.keyboard.press('Enter');

    // Wait for Codex response
    // The agent usually returns the tool output effectively.
    // We look for the payload in the last response message.
    await expect(page.locator('.prose-sm').filter({ hasText: codexPayload }).last()).toBeVisible({ timeout: 45000 });
});
