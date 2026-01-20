import { test, expect, type Locator } from "@playwright/test";
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

const logfireTemplate = resolveEnv("LOGFIRE_TRACE_URL_TEMPLATE");
const shouldValidateLogfire = process.env.PLAYWRIGHT_LOGFIRE_VALIDATION === "true";
const allowLlm = process.env.E2E_ALLOW_LLM === "true";
const backendDir = path.resolve(process.cwd(), "../backend");
const PLANNING_WAIT_TIMEOUT = 90000;
const openaiModel = resolveEnv("OPENAI_MODEL");
const anthropicModel = resolveEnv("ANTHROPIC_MODEL");
const judgeModel = resolveEnv("JUDGE_MODEL");
const dualSubagentFlag = resolveEnv("DUAL_SUBAGENT_ENABLED");
const dualSubagentEnabled = dualSubagentFlag ? dualSubagentFlag === "true" : true;
const logfireReadToken = resolveEnv("LOGFIRE_READ_TOKEN");
const logfireServiceName = resolveEnv("LOGFIRE_SERVICE_NAME");

const extractTraceId = (url: string, template: string) => {
  const parts = template.split("{trace_id}");
  if (parts.length !== 2) {
    throw new Error("LOGFIRE_TRACE_URL_TEMPLATE must include {trace_id}");
  }
  const [prefix, suffix] = parts;
  if (!url.startsWith(prefix) || !url.endsWith(suffix)) {
    throw new Error(`Trace URL did not match template: ${url}`);
  }
  return url.slice(prefix.length, url.length - suffix.length);
};

const validateTrace = (traceId: string) => {
  const traceEnv = {
    ...process.env,
    ...(logfireReadToken ? { LOGFIRE_READ_TOKEN: logfireReadToken } : {}),
    ...(logfireServiceName ? { LOGFIRE_SERVICE_NAME: logfireServiceName } : {}),
    ...(logfireTemplate ? { LOGFIRE_TRACE_URL_TEMPLATE: logfireTemplate } : {}),
  };
  execFileSync("uv", ["run", "python", "scripts/logfire_validate_trace.py", traceId], {
    cwd: backendDir,
    stdio: "inherit",
    env: traceEnv,
  });
};

const resolveTraceId = async (linkLocator: Locator, traceLocator: Locator) => {
  if ((await linkLocator.count()) > 0) {
    const link = linkLocator.first();
    const traceIdFromAttr = await link.getAttribute("data-trace-id");
    if (traceIdFromAttr) {
      return traceIdFromAttr;
    }
    const href = await link.getAttribute("href");
    if (href && logfireTemplate) {
      return extractTraceId(href, logfireTemplate);
    }
  }

  if ((await traceLocator.count()) > 0) {
    const trace = traceLocator.first();
    const traceIdFromAttr = await trace.getAttribute("data-trace-id");
    if (traceIdFromAttr) {
      return traceIdFromAttr;
    }
    const traceText = await trace.textContent();
    if (traceText) {
      const match = traceText.match(/Trace:\s*(\S+)/i);
      if (match) {
        return match[1];
      }
    }
  }

  throw new Error("Trace id not found in telemetry panel.");
};

test.describe("Sprint Board", () => {
  test.use({
    storageState: ".playwright/.auth/user.json",
  });

  test("loads and shows a created sprint", async ({ page }) => {
    if (shouldValidateLogfire) {
      test.skip(true, "Covered by full workflow Logfire validation test.");
    }
    test.setTimeout(180000);
    const sprintName = `Sprint ${Date.now()}`;

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();
    const planningPromptInput = page.locator("#planning-prompt");
    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");

    await planningPromptInput.scrollIntoViewIfNeeded();
    await planningPromptInput.click();
    await planningPromptInput.fill("Plan the next sprint outcomes");
    await expect(planningPromptInput).toHaveValue("Plan the next sprint outcomes");
    await page.getByRole("button", { name: /start planning interview/i }).click();
    await expect(page.locator("#planning-answer-0")).toBeVisible({ timeout: PLANNING_WAIT_TIMEOUT });

    const answerInputs = page.locator("[id^='planning-answer-']");
    const answerCount = await answerInputs.count();
    for (let i = 0; i < answerCount; i += 1) {
      await answerInputs.nth(i).fill("Answer for planning");
    }
    await page.getByRole("button", { name: /save answers/i }).click();
    await expect(
      page.getByText(/planning interview complete/i)
    ).toBeVisible();

    await sprintNameInput.fill("");
    await sprintNameInput.click();
    await sprintNameInput.type(sprintName);
    await expect(sprintNameInput).toHaveValue(sprintName);
    await sprintGoalInput.fill("Playwright smoke test");
    await page.getByRole("button", { name: /create sprint/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(sprintName) })).toBeVisible();
  });

  test("browser-agent sprint flow builds hello world python project", async ({ page }) => {
    if (shouldValidateLogfire) {
      test.skip(true, "Covered by full workflow Logfire validation test.");
    }
    if (!allowLlm) {
      test.skip(true, "E2E_ALLOW_LLM not enabled");
    }
    test.setTimeout(180000);
    const sprintName = `Hello World Sprint ${Date.now()}`;

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();

    const planningPromptInput = page.locator("#planning-prompt");
    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");

    await planningPromptInput.scrollIntoViewIfNeeded();
    await planningPromptInput.click();
    await planningPromptInput.fill("Build a Python project that prints hello world.");
    await expect(planningPromptInput).toHaveValue(
      "Build a Python project that prints hello world."
    );
    await page.getByRole("button", { name: /start planning interview/i }).click();
    await expect(page.locator("#planning-answer-0")).toBeVisible({ timeout: PLANNING_WAIT_TIMEOUT });

    const answerInputs = page.locator("[id^='planning-answer-']");
    const answerCount = await answerInputs.count();
    for (let i = 0; i < answerCount; i += 1) {
      await answerInputs.nth(i).fill("Answer for hello world sprint");
    }
    await page.getByRole("button", { name: /save answers/i }).click();
    await expect(page.getByText(/planning interview complete/i)).toBeVisible();

    await sprintNameInput.fill("");
    await sprintNameInput.click();
    await sprintNameInput.type(sprintName);
    await expect(sprintNameInput).toHaveValue(sprintName);
    await sprintGoalInput.fill("Build a minimal Python hello world project");
    await page.getByRole("button", { name: /create sprint/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(sprintName) })).toBeVisible();

    const sprintTelemetry = page.getByTestId("sprint-telemetry");
    await expect(sprintTelemetry).toBeVisible();
    await expect(sprintTelemetry).toContainText(/openai/i);
    await expect(sprintTelemetry).toContainText(/anthropic/i);
    if (judgeModel) {
      await expect(sprintTelemetry).toContainText(judgeModel);
    }
  });

  test("planning telemetry links validate in Logfire", async ({ page }) => {
    test.setTimeout(180000);
    if (!shouldValidateLogfire) {
      test.skip(true, "PLAYWRIGHT_LOGFIRE_VALIDATION not enabled");
    }
    if (!logfireReadToken) {
      test.skip(true, "LOGFIRE_READ_TOKEN not set");
    }
    if (dualSubagentFlag && !dualSubagentEnabled) {
      test.skip(true, "DUAL_SUBAGENT_ENABLED must be true to validate judge workflow");
    }
    if (!openaiModel || !anthropicModel || !judgeModel) {
      test.skip(true, "OPENAI_MODEL, ANTHROPIC_MODEL, and JUDGE_MODEL must be set");
    }
    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();

    const planningPromptInput = page.locator("#planning-prompt");
    const promptValue = `Validate telemetry ${Date.now()}`;
    await planningPromptInput.scrollIntoViewIfNeeded();
    await planningPromptInput.click();
    await planningPromptInput.fill(promptValue);
    await expect(planningPromptInput).toHaveValue(promptValue);
    await page.getByRole("button", { name: /start planning interview/i }).click();
    await expect(page.locator("#planning-answer-0")).toBeVisible({ timeout: PLANNING_WAIT_TIMEOUT });

    const telemetryPanel = page.getByTestId("planning-telemetry");
    await expect(telemetryPanel).toBeVisible();
    await expect(
      page.getByTestId("planning-telemetry-selected").or(
        page.getByTestId("planning-telemetry-model")
      )
    ).toBeVisible();
    await expect(telemetryPanel).toContainText(`openai (${openaiModel})`);
    await expect(telemetryPanel).toContainText(`anthropic (${anthropicModel})`);
    await expect(telemetryPanel).toContainText(`(${judgeModel})`);

    const judgeLink = page.getByTestId("planning-telemetry-judge-link");
    const judgeTrace = page.getByTestId("planning-telemetry-judge-trace");
    const openaiLink = page.getByTestId("planning-telemetry-agent-openai-link");
    const openaiTrace = page.getByTestId("planning-telemetry-agent-openai-trace");
    const anthropicLink = page.getByTestId("planning-telemetry-agent-anthropic-link");
    const anthropicTrace = page.getByTestId("planning-telemetry-agent-anthropic-trace");

    const judgeTraceId = await resolveTraceId(judgeLink, judgeTrace);
    const openaiTraceId = await resolveTraceId(openaiLink, openaiTrace);
    const anthropicTraceId = await resolveTraceId(anthropicLink, anthropicTrace);

    validateTrace(judgeTraceId);
    validateTrace(openaiTraceId);
    validateTrace(anthropicTraceId);

    const answerInputs = page.locator("[id^='planning-answer-']");
    const answerCount = await answerInputs.count();
    for (let i = 0; i < answerCount; i += 1) {
      await answerInputs.nth(i).fill("Answer for planning");
    }
    await page.getByRole("button", { name: /save answers/i }).click();
    await expect(page.getByText(/planning interview complete/i)).toBeVisible();

    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");
    const sprintName = `Sprint ${Date.now()}`;
    await sprintNameInput.fill("");
    await sprintNameInput.click();
    await sprintNameInput.type(sprintName);
    await expect(sprintNameInput).toHaveValue(sprintName);
    await sprintGoalInput.fill("Workflow + telemetry validation");
    await page.getByRole("button", { name: /create sprint/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(sprintName) })).toBeVisible();
  });
});
