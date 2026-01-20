import { test, expect } from "@playwright/test";

const LOCAL_CHAT_STORAGE_KEY = "guilde_lite_tdd_sprint-local-chats";
const ALLOW_LLM_E2E = process.env.E2E_ALLOW_LLM === "true";

test.describe("AI Chat", () => {
  // Use authenticated state
  test.use({
    storageState: ".playwright/.auth/user.json",
  });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
    }, LOCAL_CHAT_STORAGE_KEY);
    await page.goto("/chat");
  });

  test.describe("Chat Interface", () => {
    test("should show chat layout and composer", async ({ page }) => {
      await expect(page.getByText(/ai assistant/i)).toBeVisible();
      await expect(page.getByPlaceholder("Type a message...")).toBeVisible();
      await expect(page.getByRole("button", { name: /send message/i })).toBeVisible();
    });

    test("should show connection status and reset action", async ({ page }) => {
      await expect(page.getByText(/connected|disconnected/i)).toBeVisible();
      await expect(page.getByRole("button", { name: /reset/i })).toBeVisible();
    });
  });

  test.describe("Chat Functionality", () => {
    test("should allow starting a conversation when connected", async ({ page }) => {
      test.skip(!ALLOW_LLM_E2E, "Set E2E_ALLOW_LLM=true to exercise chat streaming.");
      await expect(page.getByText(/^connected$/i)).toBeVisible({ timeout: 10000 });

      const input = page.getByPlaceholder("Type a message...");
      const sendButton = page.getByRole("button", { name: /send message/i });

      await expect(input).toBeEnabled();
      await input.fill("Hello from Playwright");
      await sendButton.click();

      const userMessage = page.getByTestId("chat-message-user").last();
      await expect(userMessage).toContainText("Hello from Playwright");
    });

    test("should reset the conversation", async ({ page }) => {
      test.skip(!ALLOW_LLM_E2E, "Set E2E_ALLOW_LLM=true to exercise chat streaming.");
      await expect(page.getByText(/^connected$/i)).toBeVisible({ timeout: 10000 });

      const input = page.getByPlaceholder("Type a message...");
      await expect(input).toBeEnabled();
      await input.fill("Reset me");
      await page.getByRole("button", { name: /send message/i }).click();

      const message = page.getByTestId("chat-message-user").last();
      await expect(message).toContainText("Reset me");
      await page.getByRole("button", { name: /reset/i }).click();

      await expect(message).toBeHidden();
      await expect(page.getByText(/ai assistant/i)).toBeVisible();
    });
  });
});
