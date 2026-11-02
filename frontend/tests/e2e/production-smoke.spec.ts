import { expect, test } from "@playwright/test";

test("deployed login page responds and renders without signing in", async ({ page }) => {
  const response = await page.goto("/login");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("deployed registration page responds and renders without creating an account", async ({ page }) => {
  const response = await page.goto("/register");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  await expect(page.getByLabel("Full name")).toBeVisible();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
});


test("deployed login and registration pages fit a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  for (const route of ["/login", "/register"]) {
    const response = await page.goto(route);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.locator("body")).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
    }));
    expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
  }
});


test("protected skill routes are reachable without creating user state", async ({ page }) => {
  const mutatingRequests: string[] = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutatingRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  for (const route of ["/reading", "/listening", "/writing", "/speaking"]) {
    const response = await page.goto(route);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.locator("body")).toBeVisible();

    // Production deployments should redirect unauthenticated users. CI's
    // browser matrix runs against a local static build without auth/API context.
    if (process.env.PLAYWRIGHT_BASE_URL) {
      await expect(page).toHaveURL(/\\/login(?:\\?|$)/, { timeout: 15_000 });
      await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    } else {
      expect(new URL(page.url()).pathname).toBe(route);
    }
  }

  expect(mutatingRequests).toEqual([]);
});
