import { test, expect } from "@playwright/test";

test.describe("Sprint Board", () => {
  test.use({
    storageState: ".playwright/.auth/user.json",
  });

  test("loads and shows a created sprint", async ({ page }) => {
    const sprintName = `Sprint ${Date.now()}`;

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();
    const sprintNameInput = page.locator("#sprint-name");
    const sprintGoalInput = page.locator("#sprint-goal");

    await sprintNameInput.fill("");
    await sprintNameInput.click();
    await sprintNameInput.type(sprintName);
    await expect(sprintNameInput).toHaveValue(sprintName);
    await sprintGoalInput.fill("Playwright smoke test");
    await page.getByRole("button", { name: /create sprint/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(sprintName) })).toBeVisible();
  });
});
