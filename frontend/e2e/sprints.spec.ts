import { test, expect } from "@playwright/test";

test.describe("Sprint Board", () => {
  test.use({
    storageState: ".playwright/.auth/user.json",
  });

  test("loads and shows a created sprint", async ({ page }) => {
    const sprintName = `Sprint ${Date.now()}`;

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();
    const planningPromptInput = page.locator("#planning-prompt");
    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");

    await planningPromptInput.fill("Plan the next sprint outcomes");
    await page.getByRole("button", { name: /start planning interview/i }).click();
    await expect(page.locator("#planning-answer-0")).toBeVisible();

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
});
