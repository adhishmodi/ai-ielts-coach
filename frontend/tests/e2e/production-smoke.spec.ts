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
