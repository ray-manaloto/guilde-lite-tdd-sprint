import { test, expect } from '@playwright/test';

test('Recursive FS Write Flow', async ({ page }) => {
    test.setTimeout(120000); // Allow 2 minutes for slow agent
    // --- Authentication Step ---
    const testEmail = `fs-agent-${Date.now()}@example.com`;
    const testPassword = "TestPassword123!";

    // 1. Register User directly via Backend API
    const regResponse = await page.request.post("http://localhost:8000/api/v1/auth/register", {
        data: {
            email: testEmail,
            password: testPassword,
            full_name: "FS Agent Test User",
        },
    });

    // Log failure if needed
    if (regResponse.status() !== 200 && regResponse.status() !== 201 && regResponse.status() !== 400) {
        console.log("Registration Failed:", regResponse.status());
    }
    // 0. Setup console logging to debug WebSocket issues
    page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
    page.on('pageerror', err => console.log(`BROWSER ERROR: ${err.message}`));

    // 1. Register User (API) to ensure account exists
    await page.goto('/login');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();

    // 3. Wait for Dashboard/Chat
    await expect(page).toHaveURL(/dashboard/i, { timeout: 15000 });

    try {
        // --- Chat Flow ---
        await page.goto('/chat');

        // 4. Wait for chat input
        const input = page.getByPlaceholder("Type a message...");
        await expect(input).toBeVisible();

        // 5. Instruct Agent to write file
        // Explicitly asking to use the file system tool if possible, though "write a file" should trigger it.
        const filename = `test_file_${Date.now()}.txt`;
        const content = "Hello from recursive verification!";
        await input.fill(`You have filesystem tools enabled. Please write a file named '${filename}' with the content '${content}'. Then list the directory to confirm it's there. Finally, read the file back to me.`);

        // 6. Send message
        await page.keyboard.press('Enter');

        // 7. Wait for success response
        const responseLocator = page.locator('.prose-sm').filter({ hasText: content });

        // Increase timeout to 45s for file I/O round trip
        await expect(responseLocator).toBeVisible({ timeout: 45000 });

    } catch (e) {
        console.log("--- CHAT HISTORY DUMP ---");
        try {
            const messages = await page.locator('.prose-sm').allInnerTexts();
            if (messages.length === 0) console.log("(No messages found)");
            messages.forEach((msg, i) => console.log(`Msg ${i}:`, msg));
        } catch (inner) {
            console.log("Error dumping chat:", inner);
        }
        console.log("-------------------------");
        throw e;
    }
});
