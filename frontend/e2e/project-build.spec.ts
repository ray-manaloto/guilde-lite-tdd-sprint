
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';



test.use({ storageState: '.playwright/.auth/user.json' });

test('Project Build & Run Flow', async ({ page }) => {
    test.setTimeout(300000); // 5 minutes

    // Debug: Log browser console
    page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
    page.on('pageerror', err => console.log(`BROWSER ERROR: ${err.message}`));

    // --- Config ---
    // This must match backend/app/core/config.py AUTOCODE_ARTIFACTS_DIR
    const ARTIFACTS_ROOT = "/Users/ray.manaloto.guilde/dev/tmp/guilde-lite-tdd-sprint-filesystem";

    // 1. Navigate to Chat (User is already logged in via storageState)
    await page.goto('/chat');

    // Wait for chat input (this confirms we are authenticated and on the right page)
    const input = page.getByPlaceholder("Type a message...");
    await expect(input).toBeVisible({ timeout: 15000 });

    // 4. Prompt Agent
    const scriptName = `app_${Date.now()}.py`;
    const expectedOutput = `Build Success ${Date.now()}`;
    const prompt = `Write a python script named '${scriptName}' that prints '${expectedOutput}' to stdout. Do not use any external libraries. Confirm when done.`;

    await input.fill(prompt);
    await page.keyboard.press('Enter');

    // 5. Wait for confirmation in UI
    await expect(page.locator('.prose-sm').filter({ hasText: /done|created|wrote/i }).last()).toBeVisible({ timeout: 60000 });

    // 6. Verification (Backend Side)
    // Find the latest session directory
    if (!fs.existsSync(ARTIFACTS_ROOT)) {
        throw new Error(`Artifacts root not found: ${ARTIFACTS_ROOT}`);
    }

    const sessions = fs.readdirSync(ARTIFACTS_ROOT)
        .filter(f => fs.statSync(path.join(ARTIFACTS_ROOT, f)).isDirectory())
        .sort().reverse(); // Latest first

    if (sessions.length === 0) {
        throw new Error("No session directories found.");
    }

    // Search specifically for the file in recent sessions (in case of concurrent tests)
    let filePath = "";
    for (const session of sessions) {
        const potentialPath = path.join(ARTIFACTS_ROOT, session, scriptName);
        if (fs.existsSync(potentialPath)) {
            filePath = potentialPath;
            console.log(`Found generated script at: ${filePath}`);
            break;
        }
    }

    if (!filePath) {
        throw new Error(`Generated file '${scriptName}' not found in any recent session directory.`);
    }

    // 7. Execution (Terminal Side)
    console.log(`Executing: python3 ${filePath}`);
    try {
        const stdout = execSync(`python3 "${filePath}"`).toString().trim();
        console.log(`Script Output: ${stdout}`);
        expect(stdout).toBe(expectedOutput);
    } catch (e) {
        throw new Error(`Failed to execute generated script: ${e.message}`);
    }
});
