import { test, expect, type Locator } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";

const logfireTemplate = process.env.LOGFIRE_TRACE_URL_TEMPLATE;
const shouldValidateLogfire = process.env.PLAYWRIGHT_LOGFIRE_VALIDATION === "true";
const backendDir = path.resolve(process.cwd(), "../backend");
const PLANNING_WAIT_TIMEOUT = 90000;

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
  execFileSync("uv", ["run", "python", "scripts/logfire_validate_trace.py", traceId], {
    cwd: backendDir,
    stdio: "inherit",
    env: process.env,
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

  test("planning telemetry links validate in Logfire", async ({ page }) => {
    test.setTimeout(180000);
    if (!shouldValidateLogfire) {
      test.skip(true, "PLAYWRIGHT_LOGFIRE_VALIDATION not enabled");
    }
    if (!process.env.LOGFIRE_READ_TOKEN) {
      test.skip(true, "LOGFIRE_READ_TOKEN not set");
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
    await expect(page.getByTestId("planning-telemetry-selected")).toBeVisible();

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
  });
});
