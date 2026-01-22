import { test, expect, type APIRequestContext } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

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

const waitForService = async (request: APIRequestContext, url: string) => {
  const timeoutMs = 120_000;
  const start = Date.now();
  let lastError: string | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await request.get(url);
      if (response.status() >= 200 && response.status() < 500) {
        return;
      }
      lastError = `status ${response.status()}`;
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
  throw new Error(`Service did not become ready: ${url} (${lastError ?? "no response"})`);
};

const findGeneratedFile = (root: string, fileName: string) => {
  if (!fs.existsSync(root)) {
    return null;
  }
  const sessions = fs
    .readdirSync(root)
    .map((name) => path.join(root, name))
    .filter((dirPath) => {
      try {
        return fs.statSync(dirPath).isDirectory();
      } catch {
        return false;
      }
    })
    .sort((a, b) => {
      try {
        return fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs;
      } catch {
        return 0;
      }
    });

  for (const sessionPath of sessions) {
    const candidate = path.join(sessionPath, fileName);
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
};

test.describe("Sprint interview integration", () => {
  test.use({ storageState: ".playwright/.auth/user.json" });
  test.describe.configure({ mode: "serial" });

  test.beforeAll(async ({ request }) => {
    const artifactsRoot = resolveEnv("AUTOCODE_ARTIFACTS_DIR");
    if (!artifactsRoot) {
      throw new Error("AUTOCODE_ARTIFACTS_DIR not configured");
    }
    const agentFsEnabled = resolveEnv("AGENT_FS_ENABLED");
    if (agentFsEnabled && agentFsEnabled !== "true") {
      throw new Error("AGENT_FS_ENABLED must be true for filesystem validation");
    }

    const backendPort = resolveEnv("BACKEND_PORT") ?? "8000";
    const agentWebPort = resolveEnv("AGENT_WEB_PORT") ?? "8001";
    const frontendPort = resolveEnv("FRONTEND_PORT") ?? "3000";

    await waitForService(request, `http://localhost:${backendPort}/api/v1/health`);
    await waitForService(request, `http://localhost:${agentWebPort}/`);
    await waitForService(request, `http://localhost:${frontendPort}/api/health`);
  });

  test("agent-browser sprint interview creates hello world script", async ({ page, request }) => {
    test.setTimeout(300000);

    const artifactsRoot = resolveEnv("AUTOCODE_ARTIFACTS_DIR") ?? "";
    const repoRoot = path.resolve(process.cwd(), "..");
    const backendProject = path.join(repoRoot, "backend");

    const timestamp = Date.now();
    const scriptName = `hello_world_${timestamp}.py`;
    const expectedOutput = "hello world";
    const sprintName = `Hello World Sprint ${timestamp}`;
    const sprintPrompt = `Build a Python script named "${scriptName}" that prints "${expectedOutput}". Use only the filesystem tools, keep files in the workspace root, and avoid external libraries.`;

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();

    const planningPromptInput = page.locator("#planning-prompt");
    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");

    await planningPromptInput.scrollIntoViewIfNeeded();
    await planningPromptInput.click();
    await planningPromptInput.fill(sprintPrompt);
    await expect(planningPromptInput).toHaveValue(sprintPrompt);
    await page.getByRole("button", { name: /start planning interview/i }).click();
    await expect(page.locator("#planning-answer-0")).toBeVisible({ timeout: 90000 });

    const answerInputs = page.locator("[id^='planning-answer-']");
    const answerCount = await answerInputs.count();
    for (let i = 0; i < answerCount; i += 1) {
      await answerInputs.nth(i).fill("Answer for sprint interview");
    }
    await page.getByRole("button", { name: /save answers/i }).click();
    await expect(page.getByText(/planning interview complete/i)).toBeVisible();

    await sprintNameInput.fill("");
    await sprintNameInput.click();
    await sprintNameInput.type(sprintName);
    await expect(sprintNameInput).toHaveValue(sprintName);
    await sprintGoalInput.fill(sprintPrompt);
    await page.getByRole("button", { name: /create sprint/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(sprintName) })).toBeVisible();

    const waitStart = Date.now();
    let generatedPath: string | null = null;
    while (Date.now() - waitStart < 180000) {
      generatedPath = findGeneratedFile(artifactsRoot, scriptName);
      if (generatedPath) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    if (!generatedPath) {
      throw new Error(`Generated file '${scriptName}' not found in ${artifactsRoot}.`);
    }

    fs.accessSync(generatedPath, fs.constants.X_OK);

    const stdout = execFileSync(
      "uv",
      ["run", "--project", backendProject, "python", generatedPath],
      { encoding: "utf-8" }
    ).trim();

    expect(stdout).toBe(expectedOutput);
  });
});
