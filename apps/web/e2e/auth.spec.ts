import { expect, test } from "@playwright/test";

test("logs in and shows the overview shell", async ({ page }) => {
  await page.route("http://127.0.0.1:8080/v1/me", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ error: "unauthorized" }),
    });
  });
  await page.route("http://127.0.0.1:8080/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "X-Request-ID": "req-login" },
      body: JSON.stringify({
        user: {
          id: "user-1",
          email: "finance.operator@example.com",
          displayName: "Finance Operator",
          tenantId: "tenant-alpha",
          permissions: ["providers:read", "collections:read", "reports:read", "schedules:read", "audit:read"],
        },
      }),
    });
  });

  await page.goto("/login");
  await page.getByRole("button", { name: "Start tenant session" }).click();
  await expect(page.getByRole("heading", { name: "Roadmap baseline is live" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Providers" })).toBeVisible();
});
