import { test, expect } from "@playwright/test";

test.describe("Sprint Board", () => {
  test("loads and shows a created sprint", async ({ page, request }) => {
    const sprintName = `Sprint ${Date.now()}`;
    const createResponse = await request.post("/api/sprints", {
      data: {
        name: sprintName,
        goal: "Playwright smoke test",
      },
    });

    expect(createResponse.ok()).toBeTruthy();

    await page.goto("/sprints");
    await expect(page.getByRole("heading", { name: /sprint board/i })).toBeVisible();
    await expect(page.getByText(sprintName)).toBeVisible();
  });
});
