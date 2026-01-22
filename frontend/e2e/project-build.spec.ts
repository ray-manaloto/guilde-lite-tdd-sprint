
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';



const envFiles = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "../.env"),
    path.resolve(process.cwd(), "../backend/.env"),
];

const loadEnvFile = (filePath: string) => {
    if (!fs.existsSync(filePath)) return {};
    const output: Record<string, string> = {};
    for (const raw of fs.readFileSync(filePath, "utf-8").split(/\r?\n/)) {
        const line = raw.trim();
        if (!line || line.startsWith("#") || !line.includes("=")) continue;
        const [key, ...rest] = line.split("=");
        output[key] = rest.join("=").replace(/^['"]|['"]$/g, "");
    }
    return output;
};

const fileEnv = envFiles.reduce<Record<string, string>>(
    (acc, filePath) => ({ ...acc, ...loadEnvFile(filePath) }),
    {}
);

const resolveEnv = (key: string) => process.env[key] ?? fileEnv[key];

test.use({ storageState: '.playwright/.auth/user.json' });

test('Project Build & Run Flow', async ({ page }) => {
    test.setTimeout(300000); // 5 minutes

    // Debug: Log browser console
    page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
    page.on('pageerror', err => console.log(`BROWSER ERROR: ${err.message}`));

    // --- Config ---
    const ARTIFACTS_ROOT = resolveEnv("AUTOCODE_ARTIFACTS_DIR");
    if (!ARTIFACTS_ROOT) {
        throw new Error("AUTOCODE_ARTIFACTS_DIR not found in environment or .env files.");
    }
    const backendDir = path.resolve(process.cwd(), "../backend");

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
    console.log(`Executing: uv run --directory ${backendDir} python ${filePath}`);
    try {
        const stdout = execFileSync(
            "uv",
            ["run", "--directory", backendDir, "python", filePath],
            { encoding: "utf-8" }
        ).trim();
        console.log(`Script Output: ${stdout}`);
        expect(stdout).toBe(expectedOutput);
    } catch (e) {
        throw new Error(`Failed to execute generated script: ${e.message}`);
    }
});
