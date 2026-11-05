import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function scanSeriousAccessibility(page: Page, route: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const seriousOrCritical = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  expect(
    seriousOrCritical.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      description: violation.description,
      nodes: violation.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    })),
    `Serious/critical axe violations on deployed ${route}`,
  ).toEqual([]);
}

test("deployed login page responds and renders without signing in", async ({ page }) => {
  const response = await page.goto("/login");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await scanSeriousAccessibility(page, "/login");
});

test("deployed registration page responds and renders without creating an account", async ({ page }) => {
  const response = await page.goto("/register");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  await expect(page.getByLabel("Full name")).toBeVisible();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
  await scanSeriousAccessibility(page, "/register");
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


test("protected skill pages load without creating user state", async ({ page }) => {
  const mutatingRequests: string[] = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutatingRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  for (const route of ["/reading", "/listening", "/writing", "/speaking"]) {
    // This smoke workflow builds the frontend without starting the API server.
    // Auth redirects require an API 401; a network failure is not a redirect.
    const response = await page.goto(route);
    if (response) expect(response.status()).toBeLessThan(400);
    await expect(page).toHaveURL((url) => url.pathname === route || url.pathname === "/login");
    await expect(page.locator("main")).toBeVisible();
  }

  expect(mutatingRequests).toEqual([]);
});
